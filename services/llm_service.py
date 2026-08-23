import logging
import queue
import threading
import time
from typing import Dict, Any, Optional, Iterator, List

from services import pantry_service, settings_service

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'phi4-mini'

# --- Visibility / safety tuning -------------------------------------------------
# How often (seconds) to emit a heartbeat event even if Ollama hasn't produced a
# new token yet. This is what lets the frontend keep an "Xs elapsed" ticker alive
# instead of going silent.
HEARTBEAT_SECONDS = 8

# If this many seconds pass with zero new tokens, we surface a "this looks stuck"
# warning to the user (but keep listening — we don't kill the request for them).
STALL_WARNING_SECONDS = 45

# Hard cap on how many tokens Ollama is allowed to generate for a single response.
# Small local models can occasionally fall into a repetition loop and just keep
# generating until they fill the context window, which on CPU can take a very
# long time with zero indication anything is wrong. Capping this bounds the
# worst case. Raise it (or set to None to remove the cap) if your responses are
# routinely getting cut off.
DEFAULT_MAX_TOKENS: Optional[int] = 1000

# Small nudge against repetition loops. Harmless to leave in; set to None to
# fall back to the model's default.
REPEAT_PENALTY: Optional[float] = 1.15

SYSTEM_BASE_PROMPT = """You are LocalChef, an intelligent, helpful, and friendly local cooking assistant.
Your goal is to help the user cook delicious meals using primarily what they have available in their pantry, or to assist them in preparing shopping lists.

Guidelines:
1. Always reference and prioritize the ingredients currently available in the user's pantry.
2. If the user asks for a specific recipe (e.g. "Chicken Fajitas"), build the recipe using the items in their pantry. Clearly indicate which pantry items are being used.
3. If minor common staples (like salt, water, cooking oil, basic pepper) are needed and not in the pantry, you may mention them as optional or assumed basics.
4. If a key ingredient is missing from the pantry to make the requested dish, state clearly what's missing and suggest an alternative or note it.
5. Provide clear, structured output with:
   - Brief friendly opening acknowledgment
   - Ingredients list with measurements
   - Step-by-step numbered cooking instructions
   - Any requested extras (e.g., macros, meal-prep storage tips)
6. Strictly adhere to any user custom preferences or constraints provided below.
"""


def build_system_message() -> str:
    """Combines base instructions, current pantry contents, and user custom preferences."""
    pantry_str = pantry_service.format_pantry_for_prompt()
    custom_str = settings_service.format_custom_instructions_for_prompt()

    parts = [
        SYSTEM_BASE_PROMPT,
        "\n--- CURRENT PANTRY INVENTORY ---",
        pantry_str
    ]

    if custom_str:
        parts.extend([
            "\n--- USER CUSTOM PREFERENCES & CONSTRAINTS ---",
            custom_str
        ])

    return "\n".join(parts)


def _chat_options() -> Dict[str, Any]:
    options: Dict[str, Any] = {}
    if DEFAULT_MAX_TOKENS is not None:
        options['num_predict'] = DEFAULT_MAX_TOKENS
    if REPEAT_PENALTY is not None:
        options['repeat_penalty'] = REPEAT_PENALTY
    return options


def _ollama_worker(model: str, messages: List[Dict[str, str]], out_queue: "queue.Queue", stop_event: threading.Event):
    """Runs in a background thread and pushes raw ollama stream chunks onto out_queue.

    Kept in its own thread so the caller can enforce a wait-timeout on each
    chunk (via out_queue.get(timeout=...)) without needing ollama's blocking
    client to support that natively.
    """
    from ollama import chat, ResponseError

    try:
        stream = chat(
            model=model,
            messages=messages,
            stream=True,
            options=_chat_options(),
        )
        for chunk in stream:
            if stop_event.is_set():
                break
            out_queue.put(('chunk', chunk))
        out_queue.put(('end', None))
    except ResponseError as e:
        logger.error(f"Ollama ResponseError: {e}")
        msg = e.error if hasattr(e, 'error') else str(e)
        out_queue.put(('error', f"Ollama model error: {msg}"))
    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        out_queue.put((
            'error',
            f"Could not connect to Ollama or run model '{model}'. "
            f"Please ensure Ollama is running (`ollama serve`). Details: {str(e)}"
        ))


def _extract_chunk(chunk: Any) -> Dict[str, Any]:
    """Normalizes an ollama stream chunk (object or dict) into a plain dict."""
    if hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
        return {
            'content': chunk.message.content or '',
            'done': bool(getattr(chunk, 'done', False)),
            'eval_count': getattr(chunk, 'eval_count', None),
            'eval_duration': getattr(chunk, 'eval_duration', None),
        }
    if isinstance(chunk, dict):
        return {
            'content': (chunk.get('message') or {}).get('content', '') or '',
            'done': bool(chunk.get('done', False)),
            'eval_count': chunk.get('eval_count'),
            'eval_duration': chunk.get('eval_duration'),
        }
    return {'content': '', 'done': False, 'eval_count': None, 'eval_duration': None}


def _stream_chat(model: str, messages: List[Dict[str, str]]) -> Iterator[Dict[str, Any]]:
    """Generator of visibility events for a chat completion: status/heartbeat/
    chunk/stalled/done/error. This is the core piece that gives the frontend
    real-time insight into what's happening instead of a silent black box.
    """
    out_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    worker = threading.Thread(
        target=_ollama_worker, args=(model, messages, out_queue, stop_event), daemon=True
    )

    start_time = time.monotonic()
    last_token_time = start_time
    chars_so_far = 0
    warned_stalled = False

    worker.start()
    yield {'type': 'status', 'message': f"Sent request to Ollama ({model}) — waiting for the first tokens…", 'elapsed': 0}

    try:
        while True:
            try:
                kind, payload = out_queue.get(timeout=HEARTBEAT_SECONDS)
            except queue.Empty:
                now = time.monotonic()
                elapsed = round(now - start_time, 1)
                since_last_token = round(now - last_token_time, 1)
                if since_last_token >= STALL_WARNING_SECONDS and not warned_stalled:
                    warned_stalled = True
                    yield {
                        'type': 'stalled',
                        'message': (
                            f"No new tokens in {int(since_last_token)}s. The model is still loaded and "
                            f"running (this is common for CPU-only inference on longer responses) — "
                            f"still listening, but you can stop it below if you'd rather not wait."
                        ),
                        'elapsed': elapsed,
                    }
                else:
                    yield {'type': 'heartbeat', 'elapsed': elapsed, 'chars': chars_so_far}
                continue

            if kind == 'error':
                yield {'type': 'error', 'message': payload}
                return

            if kind == 'end':
                yield {'type': 'done', 'elapsed': round(time.monotonic() - start_time, 1), 'chars': chars_so_far}
                return

            # kind == 'chunk'
            data = _extract_chunk(payload)
            content = data['content']

            if content:
                last_token_time = time.monotonic()
                warned_stalled = False
                chars_so_far += len(content)
                yield {
                    'type': 'chunk',
                    'content': content,
                    'elapsed': round(time.monotonic() - start_time, 1),
                    'chars': chars_so_far,
                }

            if data['done']:
                tokens = data['eval_count']
                tok_per_sec = None
                if tokens and data['eval_duration']:
                    tok_per_sec = round(tokens / (data['eval_duration'] / 1e9), 1)
                yield {
                    'type': 'done',
                    'elapsed': round(time.monotonic() - start_time, 1),
                    'chars': chars_so_far,
                    'tokens': tokens,
                    'tokens_per_sec': tok_per_sec,
                }
                return
    finally:
        # Stop the background thread from pushing further chunks. Note: this does
        # NOT cancel generation on the Ollama server itself (the ollama-python
        # client / HTTP API doesn't expose a cancel call as of this writing) —
        # it just stops us from waiting on it. The worker thread is a daemon
        # thread so it won't block app shutdown either way.
        stop_event.set()


def stream_recipe(user_prompt: str, model: str = DEFAULT_MODEL) -> Iterator[Dict[str, Any]]:
    """Yields visibility events while generating a recipe from Ollama."""
    system_message = build_system_message()
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_prompt}
    ]
    yield from _stream_chat(model, messages)


def stream_shopping_list(custom_prompt: Optional[str] = None, model: str = DEFAULT_MODEL) -> Iterator[Dict[str, Any]]:
    """Yields visibility events while generating a shopping list from Ollama."""
    system_message = build_system_message()

    user_instruction = (
        "I am going grocery shopping. Look at my current pantry inventory above. "
        "Recommend a sensible grocery shopping list of items I might need to complete versatile meals "
        "or restock essentials that appear missing/low based on what I have."
    )
    if custom_prompt and custom_prompt.strip():
        user_instruction += f"\nAdditional note for this shopping trip: {custom_prompt.strip()}"

    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_instruction}
    ]
    yield from _stream_chat(model, messages)
