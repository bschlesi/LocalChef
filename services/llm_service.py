import logging
from typing import Dict, Any, Optional
from services import pantry_service, settings_service

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'phi4-mini'

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


def generate_recipe(user_prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Generates a recipe using Ollama and the user's current pantry context."""
    from ollama import chat, ResponseError

    system_message = build_system_message()
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_prompt}
    ]

    try:
        response = chat(
            model=model,
            messages=messages,
        )
        # Access message content
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            return response.message.content
        elif isinstance(response, dict) and 'message' in response:
            return response['message']['content']
        return str(response)
    except ResponseError as e:
        logger.error(f"Ollama ResponseError: {e}")
        raise RuntimeError(f"Ollama model error: {e.error if hasattr(e, 'error') else str(e)}")
    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        raise RuntimeError(f"Could not connect to Ollama or run model '{model}'. Please ensure Ollama is running (`ollama serve`). Details: {str(e)}")


def generate_shopping_list(custom_prompt: Optional[str] = None, model: str = DEFAULT_MODEL) -> str:
    """Generates a shopping list based on the current pantry inventory and missing staples."""
    from ollama import chat, ResponseError

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

    try:
        response = chat(
            model=model,
            messages=messages,
        )
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            return response.message.content
        elif isinstance(response, dict) and 'message' in response:
            return response['message']['content']
        return str(response)
    except ResponseError as e:
        logger.error(f"Ollama ResponseError: {e}")
        raise RuntimeError(f"Ollama model error: {e.error if hasattr(e, 'error') else str(e)}")
    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        raise RuntimeError(f"Could not connect to Ollama or run model '{model}'. Please ensure Ollama is running (`ollama serve`). Details: {str(e)}")
