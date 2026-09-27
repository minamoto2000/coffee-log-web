from datetime import datetime, timezone
import sqlite3

import database
import pytest
from fastapi.testclient import TestClient

from main import app
from models import BrewLogRead, EvaluationRead
from recommendation import build_recommendation


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()

    with TestClient(app) as test_client:
        yield test_client


def _create_equipment_set(client, grind_setting_unit="click"):
    response = client.post(
        "/equipment-sets",
        json={
            "name": "Test Set",
            "filter_label": "Paper",
            "brewer_label": "V60",
            "grinder_label": "Test Grinder",
            "grind_setting_unit": grind_setting_unit,
            "note": None,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_log(client, equipment_set_id, brewed_at):
    response = client.post(
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
                "brewed_at": brewed_at,
            },
            "evaluation": {
                "confidence": 2,
                "overall_score": 7,
                "taste_defect": "none",
                "aroma_defect": False,
                "aftertaste_defect": False,
                "texture_defect": False,
                "memo": None,
            },
        },
    )
    assert response.status_code == 200
    return response.json()["brew_log"]["id"]


def _brew_log(
    *,
    water_temp_c=92,
    agitation_level=1,
    grind_setting_value=20,
    grind_setting_unit_snapshot="click",
):
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    return BrewLogRead(
        id=1,
        equipment_set_id=1,
        bean_label="Test Beans",
        dose_g=15,
        water_g=250,
        water_temp_c=water_temp_c,
        grind_setting_value=grind_setting_value,
        bloom_time_s=30,
        agitation_level=agitation_level,
        pours=[
            {"grams": 50, "at_s": 0},
            {"grams": 100, "at_s": 45},
            {"grams": 100, "at_s": 90},
        ],
        finish_pouring_s=120,
        brew_end_s=180,
        note=None,
        brewed_at=now,
        equipment_set_name_snapshot="Test Set",
        brewer_label_snapshot="V60",
        grind_setting_unit_snapshot=grind_setting_unit_snapshot,
        filter_label_snapshot="Paper",
        grinder_label_snapshot="Test Grinder",
        created_at=now,
        updated_at=now,
    )


def _evaluation(**overrides):
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    data = {
        "id": 1,
        "brew_log_id": 1,
        "confidence": 2,
        "overall_score": 7,
        "taste_defect": "none",
        "aroma_defect": False,
        "aftertaste_defect": False,
        "texture_defect": False,
        "memo": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return EvaluationRead(**data)


def test_brew_log_list_is_ordered_by_brewed_at_then_id_desc(client):
    equipment_set_id = _create_equipment_set(client)
    older_id = _create_log(client, equipment_set_id, "2026-09-25T08:00:00+00:00")
    first_latest_id = _create_log(client, equipment_set_id, "2026-09-26T08:00:00+00:00")
    second_latest_id = _create_log(client, equipment_set_id, "2026-09-26T08:00:00+00:00")

    response = client.get("/logs")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        second_latest_id,
        first_latest_id,
        older_id,
    ]


def test_latest_recommendation_uses_specified_endpoint_and_ordering(client):
    equipment_set_id = _create_equipment_set(client)
    _create_log(client, equipment_set_id, "2026-09-25T08:00:00+00:00")
    _create_log(client, equipment_set_id, "2026-09-26T08:00:00+00:00")
    latest_id = _create_log(client, equipment_set_id, "2026-09-26T08:00:00+00:00")

    response = client.get("/recommendations/latest")

    assert response.status_code == 200
    assert response.json()["target_log_id"] == latest_id


def test_benchmark_score_trend_returns_required_fields_in_ascending_date_order(client):
    first = client.post(
        "/benchmarks",
        json={
            "consumed_at": "2026-09-27",
            "source_type": "cafe",
            "product_name": "Later",
            "overall_score": 8,
            "note": "not returned by trend",
        },
    )
    second = client.post(
        "/benchmarks",
        json={
            "consumed_at": "2026-09-25",
            "source_type": "other",
            "product_name": "Earlier",
            "overall_score": 6,
            "note": None,
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get("/benchmarks/trends/score")

    assert response.status_code == 200
    data = response.json()
    assert [item["product_name"] for item in data] == ["Earlier", "Later"]
    assert set(data[0]) == {
        "benchmark_id",
        "consumed_at",
        "product_name",
        "overall_score",
    }


def test_recommendation_falls_back_when_water_temperature_would_exceed_100():
    result = build_recommendation(
        _brew_log(water_temp_c=99),
        _evaluation(taste_defect="sour"),
    )

    assert result.action_type == "keep_same"
    assert result.recommendation_mode == "experiment"


def test_recommendation_falls_back_when_agitation_would_be_negative():
    result = build_recommendation(
        _brew_log(agitation_level=0),
        _evaluation(texture_defect=True),
    )

    assert result.action_type == "keep_same"
    assert result.recommendation_mode == "experiment"


def test_recommendation_falls_back_for_other_grind_unit():
    result = build_recommendation(
        _brew_log(grind_setting_unit_snapshot="other"),
        _evaluation(taste_defect="thin"),
    )

    assert result.action_type == "keep_same"
    assert result.recommendation_mode == "experiment"


def test_recommendation_uses_experiment_mode_when_no_action_can_be_selected():
    result = build_recommendation(
        _brew_log(),
        _evaluation(overall_score=7),
    )

    assert result.action_type == "keep_same"
    assert result.recommendation_mode == "experiment"



def test_equipment_set_required_strings_are_trimmed_and_blank_values_rejected(client):
    valid_response = client.post(
        "/equipment-sets",
        json={
            "name": "  Test Set  ",
            "filter_label": "  Paper  ",
            "brewer_label": "  V60  ",
            "grinder_label": "  Grinder  ",
            "grind_setting_unit": "click",
            "note": None,
        },
    )
    assert valid_response.status_code == 200
    assert valid_response.json()["name"] == "Test Set"
    assert valid_response.json()["filter_label"] == "Paper"

    invalid_response = client.post(
        "/equipment-sets",
        json={
            "name": "   ",
            "filter_label": "Paper",
            "brewer_label": "V60",
            "grinder_label": "Grinder",
            "grind_setting_unit": "click",
            "note": None,
        },
    )
    assert invalid_response.status_code == 422


def test_brewed_at_and_response_timestamps_are_normalized_to_utc(client):
    equipment_set_id = _create_equipment_set(client)
    response = client.post(
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
                "brewed_at": "2026-09-27T18:00:00+09:00",
            },
            "evaluation": {
                "confidence": 2,
                "overall_score": 7,
                "taste_defect": "none",
                "aroma_defect": False,
                "aftertaste_defect": False,
                "texture_defect": False,
                "memo": None,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    brewed_at = datetime.fromisoformat(
        data["brew_log"]["brewed_at"].replace("Z", "+00:00")
    )
    log_created_at = datetime.fromisoformat(
        data["brew_log"]["created_at"].replace("Z", "+00:00")
    )
    evaluation_created_at = datetime.fromisoformat(
        data["evaluation"]["created_at"].replace("Z", "+00:00")
    )

    assert brewed_at.utcoffset().total_seconds() == 0
    assert brewed_at.hour == 9
    assert log_created_at.utcoffset().total_seconds() == 0
    assert evaluation_created_at.utcoffset().total_seconds() == 0



def test_brew_log_patch_validates_the_merged_resource(client):
    equipment_set_id = _create_equipment_set(client)
    brew_log_id = _create_log(
        client,
        equipment_set_id,
        "2026-09-27T08:00:00+00:00",
    )

    response = client.patch(
        f"/logs/{brew_log_id}",
        json={"water_g": 260},
    )

    assert response.status_code == 422

    unchanged = client.get(f"/logs/{brew_log_id}")
    assert unchanged.status_code == 200
    assert unchanged.json()["water_g"] == 250


def test_brew_log_delete_cascades_to_evaluation(client):
    equipment_set_id = _create_equipment_set(client)
    brew_log_id = _create_log(
        client,
        equipment_set_id,
        "2026-09-27T08:00:00+00:00",
    )

    delete_response = client.delete(f"/logs/{brew_log_id}")
    assert delete_response.status_code == 200

    evaluation_response = client.get(f"/logs/{brew_log_id}/evaluation")
    assert evaluation_response.status_code == 404

    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM evaluations WHERE brew_log_id = ?",
            (brew_log_id,),
        ).fetchone()
    assert row["count"] == 0


def test_brew_log_and_evaluation_creation_rolls_back_as_one_transaction(client):
    equipment_set_id = _create_equipment_set(client)

    with database.get_connection() as conn:
        conn.execute(
            """
            CREATE TRIGGER force_evaluation_insert_failure
            BEFORE INSERT ON evaluations
            BEGIN
                SELECT RAISE(ABORT, 'forced evaluation failure');
            END;
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        _create_log(
            client,
            equipment_set_id,
            "2026-09-27T08:00:00+00:00",
        )

    with database.get_connection() as conn:
        brew_log_count = conn.execute(
            "SELECT COUNT(*) AS count FROM brew_logs"
        ).fetchone()["count"]
        evaluation_count = conn.execute(
            "SELECT COUNT(*) AS count FROM evaluations"
        ).fetchone()["count"]

    assert brew_log_count == 0
    assert evaluation_count == 0



def test_core_vertical_slice_pages_render(client):
    equipment_set_id = _create_equipment_set(client)
    brew_log_id = _create_log(
        client,
        equipment_set_id,
        "2026-09-27T08:00:00+00:00",
    )

    urls = [
        "/",
        "/pages/equipment-sets",
        "/pages/equipment-sets/new",
        f"/pages/equipment-sets/{equipment_set_id}/edit",
        "/pages/logs",
        "/pages/logs/new",
        f"/pages/logs/{brew_log_id}",
        f"/pages/logs/{brew_log_id}/recommendation",
    ]

    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, url
