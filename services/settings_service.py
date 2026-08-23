import os
import json
from typing import Dict, Any

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'user_settings.json')

DEFAULT_SETTINGS: Dict[str, Any] = {
    'custom_instructions': '',
    'meal_prep_mode': False,
    'report_macros': False
}


def ensure_config_exists():
    """Ensures config directory and user_settings.json exist."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)


def get_settings() -> Dict[str, Any]:
    """Loads settings from config/user_settings.json."""
    ensure_config_exists()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Saves updated settings to config/user_settings.json."""
    ensure_config_exists()
    current = get_settings()
    
    if 'custom_instructions' in new_settings:
        current['custom_instructions'] = str(new_settings['custom_instructions']).strip()
    if 'meal_prep_mode' in new_settings:
        current['meal_prep_mode'] = bool(new_settings['meal_prep_mode'])
    if 'report_macros' in new_settings:
        current['report_macros'] = bool(new_settings['report_macros'])
        
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=2)
    return current


def format_custom_instructions_for_prompt() -> str:
    """Builds a formatted string of user custom instructions/toggles for LLM injection."""
    settings = get_settings()
    injections = []
    
    if settings.get('custom_instructions'):
        injections.append(f"User Custom Instructions: {settings['custom_instructions']}")
    
    if settings.get('meal_prep_mode'):
        injections.append("User Preference: Optimize recipe for meal-prepping (include instructions on how to divide into portions and store).")
        
    if settings.get('report_macros'):
        injections.append("User Preference: Always report estimated macronutrients (calories, protein, carbs, fat) and portion sizing.")
        
    if not injections:
        return ""
    
    return "\n".join(injections)
