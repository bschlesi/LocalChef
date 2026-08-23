import os
import pytest
from services import settings_service


@pytest.fixture(autouse=True)
def setup_test_settings(tmp_path, monkeypatch):
    test_config_dir = str(tmp_path / "config")
    test_settings_path = os.path.join(test_config_dir, "user_settings.json")
    monkeypatch.setattr(settings_service, "CONFIG_DIR", test_config_dir)
    monkeypatch.setattr(settings_service, "SETTINGS_FILE", test_settings_path)
    settings_service.ensure_config_exists()
    yield


def test_default_settings():
    settings = settings_service.get_settings()
    assert settings["custom_instructions"] == ""
    assert settings["meal_prep_mode"] is False
    assert settings["report_macros"] is False


def test_save_settings():
    updated = settings_service.save_settings({
        "custom_instructions": "Only stovetop recipes",
        "meal_prep_mode": True,
        "report_macros": True
    })
    assert updated["custom_instructions"] == "Only stovetop recipes"
    assert updated["meal_prep_mode"] is True
    assert updated["report_macros"] is True

    loaded = settings_service.get_settings()
    assert loaded == updated


def test_format_custom_instructions_for_prompt():
    settings_service.save_settings({
        "custom_instructions": "No dairy products",
        "meal_prep_mode": True,
        "report_macros": False
    })
    prompt_str = settings_service.format_custom_instructions_for_prompt()
    assert "No dairy products" in prompt_str
    assert "meal-prepping" in prompt_str
    assert "macronutrients" not in prompt_str
