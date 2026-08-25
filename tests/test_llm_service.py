import pytest
from services import llm_service, pantry_service, settings_service


def test_chat_options():
    opts = llm_service._chat_options()
    assert opts.get('num_predict') == 1300
    assert opts.get('repeat_penalty') == 1.15
    assert opts.get('temperature') == 0.2


def test_build_system_message_for_recipe(tmp_path, monkeypatch):
    test_data_dir = str(tmp_path / "data")
    test_csv = str(tmp_path / "data" / "pantry.csv")
    monkeypatch.setattr(pantry_service, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(pantry_service, "PANTRY_CSV_PATH", test_csv)
    pantry_service.ensure_pantry_file_exists()
    pantry_service.add_item("Rigatoni", 16, "oz")

    test_config_dir = str(tmp_path / "config")
    test_settings_path = str(tmp_path / "config" / "user_settings.json")
    monkeypatch.setattr(settings_service, "CONFIG_DIR", test_config_dir)
    monkeypatch.setattr(settings_service, "SETTINGS_FILE", test_settings_path)
    settings_service.ensure_config_exists()
    settings_service.save_settings({"custom_instructions": "Make it spicy"})

    system_msg = llm_service.build_system_message(for_shopping=False)
    assert "MANDATORY RULES FOR RECIPE GENERATION:" in system_msg
    assert "STRICT PANTRY ADHERENCE:" in system_msg
    assert "EXAMPLE OF A HIGH-QUALITY RECIPE RESPONSE" in system_msg
    assert "Rigatoni: 16 oz" in system_msg
    assert "Make it spicy" in system_msg


def test_build_system_message_for_shopping(tmp_path, monkeypatch):
    test_data_dir = str(tmp_path / "data")
    test_csv = str(tmp_path / "data" / "pantry.csv")
    monkeypatch.setattr(pantry_service, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(pantry_service, "PANTRY_CSV_PATH", test_csv)
    pantry_service.ensure_pantry_file_exists()
    pantry_service.add_item("Black Beans", 2, "cans")

    test_config_dir = str(tmp_path / "config")
    test_settings_path = str(tmp_path / "config" / "user_settings.json")
    monkeypatch.setattr(settings_service, "CONFIG_DIR", test_config_dir)
    monkeypatch.setattr(settings_service, "SETTINGS_FILE", test_settings_path)
    settings_service.ensure_config_exists()

    system_msg = llm_service.build_system_message(for_shopping=True)
    assert "MANDATORY RULES FOR SHOPPING LIST GENERATION:" in system_msg
    assert "Smart Grocery Shopping List" in system_msg
    assert "Black Beans: 2 cans" in system_msg
    # Should not include the recipe one-shot example in shopping list mode
    assert "EXAMPLE OF A HIGH-QUALITY RECIPE RESPONSE" not in system_msg
