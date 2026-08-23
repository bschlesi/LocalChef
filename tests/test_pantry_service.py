import os
import pytest
from services import pantry_service


@pytest.fixture(autouse=True)
def setup_test_pantry(tmp_path, monkeypatch):
    test_data_dir = str(tmp_path / "data")
    test_csv_path = os.path.join(test_data_dir, "pantry.csv")
    monkeypatch.setattr(pantry_service, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(pantry_service, "PANTRY_CSV_PATH", test_csv_path)
    pantry_service.ensure_pantry_file_exists()
    yield
    pantry_service.clear_pantry()


def test_empty_pantry():
    items = pantry_service.get_all_items()
    assert items == []


def test_add_and_get_item():
    item = pantry_service.add_item("Chicken breast", 2, "lbs", "2026-01-01")
    assert item["item"] == "Chicken breast"
    assert item["quantity"] == 2
    assert item["units"] == "lbs"

    items = pantry_service.get_all_items()
    assert len(items) == 1
    assert items[0]["item"] == "Chicken breast"


def test_update_existing_item():
    pantry_service.add_item("Onion", 1, "count")
    pantry_service.add_item("Onion", 3, "count")
    
    items = pantry_service.get_all_items()
    assert len(items) == 1
    assert items[0]["quantity"] == 3


def test_remove_item():
    pantry_service.add_item("Onion", 2, "count")
    pantry_service.add_item("Garlic", 5, "cloves")
    
    remaining = pantry_service.remove_items(["Onion"])
    assert len(remaining) == 1
    assert remaining[0]["item"] == "Garlic"


def test_clear_pantry():
    pantry_service.add_item("Item 1", 1)
    pantry_service.add_item("Item 2", 2)
    pantry_service.clear_pantry()
    assert pantry_service.get_all_items() == []


def test_import_csv(tmp_path, monkeypatch):
    test_data_dir = pantry_service.DATA_DIR
    import_file = os.path.join(test_data_dir, "pantry_import.csv")
    with open(import_file, "w", encoding="utf-8") as f:
        f.write("Date Added/Updated,Item,Quantity,Unit(s)\n")
        f.write("2026-01-01,Bell pepper,2,count\n")
        f.write("2026-01-02,Soy sauce,16,oz\n")

    result = pantry_service.import_csv("pantry_import.csv")
    assert result["count"] == 2

    items = pantry_service.get_all_items()
    assert len(items) == 2
    assert items[0]["item"] == "Bell pepper"
    assert items[1]["item"] == "Soy sauce"


def test_format_pantry_for_prompt():
    pantry_service.add_item("Chicken", 1, "lb", "2026-01-01")
    prompt_str = pantry_service.format_pantry_for_prompt()
    assert "Chicken: 1 lb" in prompt_str
