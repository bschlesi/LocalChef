import os
import pytest
from app import app
from services import pantry_service, settings_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_data_dir = str(tmp_path / "data")
    test_config_dir = str(tmp_path / "config")
    
    monkeypatch.setattr(pantry_service, "DATA_DIR", test_data_dir)
    monkeypatch.setattr(pantry_service, "PANTRY_CSV_PATH", os.path.join(test_data_dir, "pantry.csv"))
    monkeypatch.setattr(settings_service, "CONFIG_DIR", test_config_dir)
    monkeypatch.setattr(settings_service, "SETTINGS_FILE", os.path.join(test_config_dir, "user_settings.json"))

    pantry_service.ensure_pantry_file_exists()
    settings_service.ensure_config_exists()

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_pages_render(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b"Cooking" in res.data

    res = client.get('/pantry')
    assert res.status_code == 200
    assert b"Current Pantry" in res.data

    res = client.get('/customization')
    assert res.status_code == 200
    assert b"Custom Instructions" in res.data


def test_pantry_api_flow(client):
    # Get empty
    res = client.get('/api/pantry')
    assert res.status_code == 200
    assert res.get_json()['items'] == []

    # Add item
    res = client.post('/api/pantry', json={
        'item': 'Taco seasoning',
        'quantity': 12,
        'units': 'oz'
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True

    # Check pantry
    res = client.get('/api/pantry')
    items = res.get_json()['items']
    assert len(items) == 1
    assert items[0]['item'] == 'Taco seasoning'

    # Remove item
    res = client.delete('/api/pantry', json={'items': ['Taco seasoning']})
    assert res.status_code == 200
    assert len(res.get_json()['items']) == 0


def test_settings_api_flow(client):
    res = client.get('/api/settings')
    assert res.status_code == 200
    assert res.get_json()['settings']['meal_prep_mode'] is False

    res = client.post('/api/settings', json={
        'custom_instructions': 'High protein only',
        'meal_prep_mode': True,
        'report_macros': True
    })
    assert res.status_code == 200
    assert res.get_json()['settings']['meal_prep_mode'] is True
