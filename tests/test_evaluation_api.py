import database
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def brew_log_id(client):
    equipment_response = client.post(
        "/equipment-sets",
        json={
            "name": "Test Set",
            "filter_label": "Paper",
            "brewer_label": "V60",
            "grinder_label": "Test Grinder",
            "grind_setting_unit": "click",
            "note": None,
        },
    )
    assert equipment_response.status_code == 200
    equipment_set_id = equipment_response.json()["id"]

    log_response = client.post(
        "/logs",
        json={
            "brew_log": {
                "equipment_set_id": equipment_set_id,
                "bean_label": "Test Beans",
                "dose_g": 15,
                "water_g": 250,
                "water_temp_c": 92,
                "grind_setting_value": 20,
                "bloom_time_s": 30,
                "agitation_level": 1,
                "pours": [
                    {"grams": 50, "at_s": 0},
                    {"grams": 100, "at_s": 45},
                    {"grams": 100, "at_s": 90},
                ],
                "finish_pouring_s": 120,
                "brew_end_s": 180,
                "note": None,
                "brewed_at": "2026-09-08T08:00:00+00:00",
            },
            "evaluation": {
                "confidence": 1,
                "overall_score": 8,
                "taste_defect": "none",
                "aroma_defect": False,
                "aftertaste_defect": False,
                "texture_defect": False,
                "memo": "original",
            },
        },
    )
    assert log_response.status_code == 200

    response_data = log_response.json()
    if "brew_log" in response_data:
        return response_data["brew_log"]["id"]
    return response_data["id"]


def test_get_evaluation_returns_created_evaluation(client, brew_log_id):
    response = client.get(f"/logs/{brew_log_id}/evaluation")

    assert response.status_code == 200
    data = response.json()
    assert data["brew_log_id"] == brew_log_id
    assert data["confidence"] == 1
    assert data["overall_score"] == 8
    assert data["memo"] == "original"


def test_patch_evaluation_updates_only_provided_field(client, brew_log_id):
    response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={"memo": "changed"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["memo"] == "changed"
    assert data["confidence"] == 1
    assert data["overall_score"] == 8
    assert data["taste_defect"] == "none"
    assert data["aroma_defect"] is False
    assert data["aftertaste_defect"] is False
    assert data["texture_defect"] is False


def test_patch_evaluation_empty_body_returns_400(client, brew_log_id):
    response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update"


def test_patch_evaluation_rejects_null_for_required_field(client, brew_log_id):
    response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={"confidence": None},
    )

    assert response.status_code == 422


def test_patch_evaluation_allows_null_for_nullable_field(client, brew_log_id):
    response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={"overall_score": None},
    )

    assert response.status_code == 200
    assert response.json()["overall_score"] is None


def test_patch_evaluation_validates_merged_resource(client, brew_log_id):
    clear_score_response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={"overall_score": None},
    )
    assert clear_score_response.status_code == 200

    response = client.patch(
        f"/logs/{brew_log_id}/evaluation",
        json={"confidence": 2},
    )

    assert response.status_code == 422


def test_patch_evaluation_missing_resource_returns_404(client):
    response = client.patch(
        "/logs/999999/evaluation",
        json={"memo": "changed"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found"
