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
HEARTBEAT_SECONDS = 10

# If this many seconds pass with zero new tokens, we surface a "this looks stuck"
# warning to the user (but keep listening — we don't kill the request for them).
STALL_WARNING_SECONDS = 60

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

# Sampling temperature: 0.2 provides high adherence to pantry items and structured formatting.
DEFAULT_TEMPERATURE: Optional[float] = 0.2

SYSTEM_BASE_PROMPT = """You are LocalChef, a precise and expert local cooking assistant.
Your top priority is generating high-quality recipes tailored strictly to the user's pantry inventory.

MANDATORY RULES FOR RECIPE GENERATION:
1. STRICT PANTRY ADHERENCE: You MUST ONLY use ingredients that exist in the CURRENT PANTRY INVENTORY. Never assume, invent, or hallucinate ingredients (do not assume butter, eggs, oil, milk, or seasonings exist unless they appear in the pantry inventory).
2. QUANTITY CONSTRAINTS: Respect the available amounts in the pantry. Do not specify amounts exceeding what is in stock.
3. STRUCTURED RECIPE FORMAT: Always structure your recipe with these exact markdown sections:
   - # [Recipe Title]
   - A brief 1-2 sentence description.
   - ---
   - ## Ingredients (formatted as a Markdown table with columns: | Ingredient | Amount | From Pantry |)
   - ---
   - ## Equipment Needed (bullet points)
   - ---
   - ## Instructions (numbered steps with bold titles, e.g., '### 1. Prep', '### 2. Cook Chicken')
   - ---
   - ## Yield & Macros (Markdown table with columns: | Metric | Per Serving | Total Recipe | for Servings, Calories, Protein, Carbs, Fat)
   - ---
   - ## Beginner Tips (practical cooking tips, bullet points)
4. NO UNNECESSARY FILLER: Be concise, clear, and direct in instructions.
5. STRICT CONSTRAINTS: Adhere 100% to any user custom preferences or diet constraints provided below.
"""

SHOPPING_BASE_PROMPT = """You are LocalChef, an intelligent grocery shopping assistant.
Your goal is to analyze the user's CURRENT PANTRY INVENTORY and recommend a practical, organized grocery shopping list.

MANDATORY RULES FOR SHOPPING LIST GENERATION:
1. RESTOCK & COMPLEMENT: Recommend essential staple restocks, missing ingredients to complete balanced meals, or companion ingredients that pair well with existing pantry items.
2. CATEGORIZED FORMAT: Structure the grocery list by supermarket department using markdown headers:
   - # Smart Grocery Shopping List
   - Brief 1-2 sentence overview of the shopping strategy.
   - ## Produce (Fruits & Vegetables)
   - ## Meat & Seafood / Proteins
   - ## Dairy & Refrigerated
   - ## Pantry Staples & Grains
   - ## Canned Goods & Sauces
   - ## Spices, Oils & Condiments
   - ## Meal Ideas Unlocked (1-2 bullet points explaining what new dishes can be made with these additions)
3. ITEM DETAILS & REASONING: Format each item as a bullet point with suggested purchase quantity and the reason it was suggested based on current pantry contents (e.g. "- **Yellow Onions** (3 lbs bag) — Essential aromatic base to pair with your canned black beans and rice").
4. RESPECT CONSTRAINTS: Adhere 100% to any user custom preferences or diet constraints provided below.
"""

ONE_SHOT_RECIPE_EXAMPLE = """
--- EXAMPLE OF A HIGH-QUALITY RECIPE RESPONSE ---
User Request: Chicken pasta bake

Assistant Response:
# Cheesy Chicken Pasta Bake

Here's a hearty, beginner-friendly chicken pasta bake using only ingredients from your pantry.

---

## Ingredients

| Ingredient | Amount | From Pantry |
|---|---|---|
| Rigatoni | 12 oz | Rigatoni — 16 oz available |
| Boneless Skinless Chicken Breast | 1.5 lbs | 3 lbs available |
| Good & Gather Three Cheese Tomato Pasta Sauce | 24 oz | 24 oz available |
| Fat-Free Milk | 1/2 cup | 0.5 gallons available |
| Shredded Mozzarella | 8 oz | 8 oz available |
| Grated Parmesan | 4 oz | 24 oz available |
| Salt | 1 tsp | available |
| Black Pepper | 1/2 tsp | available |
| Garlic Powder | 1 tsp | available |
| Italian Seasoning | 1 tsp | available |

---

## Equipment Needed
- Large pot for pasta
- Large skillet or pan for chicken
- 9x13 inch baking dish (or any large oven-safe dish)
- Colander
- Cutting board and knife

---

## Instructions

### 1. Prep
Preheat your oven to **375°F (190°C)**. Lightly grease your baking dish.

### 2. Cook the Pasta
Bring a large pot of salted water to a boil. Add the **12 oz of rigatoni** and cook according to package directions until **al dente** (10–12 minutes). Drain and set aside.

### 3. Cook the Chicken
Cut the **1.5 lbs of chicken breast** into 1-inch bite-sized cubes. Heat a large skillet over medium-high heat. Season chicken cubes with salt, black pepper, garlic powder, and Italian seasoning. Cook for 6–8 minutes, stirring occasionally, until cooked through. Remove from heat.

### 4. Make the Sauce
In a large bowl, combine the tomato pasta sauce, fat-free milk, and 2 oz of grated Parmesan. Stir until smooth.

### 5. Assemble the Bake
In your baking dish, combine cooked rigatoni, cooked chicken, and sauce mixture. Toss until evenly coated.

### 6. Top with Cheese
Sprinkle the shredded mozzarella and remaining 2 oz of grated Parmesan evenly over the top.

### 7. Bake
Bake in the preheated oven for 20–25 minutes until the cheese is bubbly and golden brown around the edges. Let cool for 5 minutes before serving.

---

## Beginner Tips
- **Don't overcook the pasta** in step 2 — it will finish cooking in the oven.
- **Cut chicken evenly** so all pieces cook at the same speed.
- **Let it rest** 5 minutes after baking so the sauce thickens and portions hold together.
---
"""


def build_system_message(for_shopping: bool = False) -> str:
    """Combines base instructions, current pantry contents, and user custom preferences."""
    pantry_str = pantry_service.format_pantry_for_prompt()
    custom_str = settings_service.format_custom_instructions_for_prompt()

    base = SHOPPING_BASE_PROMPT if for_shopping else SYSTEM_BASE_PROMPT
    parts = [
        base,
        "\n--- CURRENT PANTRY INVENTORY ---",
        pantry_str
    ]

    if not for_shopping:
        parts.append(ONE_SHOT_RECIPE_EXAMPLE)

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
    if DEFAULT_TEMPERATURE is not None:
        options['temperature'] = DEFAULT_TEMPERATURE
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
    system_message = build_system_message(for_shopping=False)
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_prompt}
    ]
    yield from _stream_chat(model, messages)


def stream_shopping_list(custom_prompt: Optional[str] = None, model: str = DEFAULT_MODEL) -> Iterator[Dict[str, Any]]:
    """Yields visibility events while generating a shopping list from Ollama."""
    system_message = build_system_message(for_shopping=True)

    user_instruction = (
        "I am planning my grocery shopping trip. Look at my current pantry inventory above. "
        "Recommend a structured shopping list of items to restock essentials and complete versatile meals."
    )
    if custom_prompt and custom_prompt.strip():
        user_instruction += f"\nAdditional note for this shopping trip: {custom_prompt.strip()}"

    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_instruction}
    ]
    yield from _stream_chat(model, messages)
