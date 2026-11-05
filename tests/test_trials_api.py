import pytest
from fastapi.testclient import TestClient

from app import db as database
from app.main import app
from app.repositories import trials as trial_repository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    with TestClient(app) as test_client:
        yield test_client


def steps(first_pour_temp):
    return [
        {"step_type": "pour", "start_s": 0, "water_g": 30, "kettle_temp_c": first_pour_temp},
        {"step_type": "pour", "start_s": 120, "water_g": 100, "kettle_temp_c": 93},
        {"step_type": "pour", "start_s": 150, "water_g": 120, "kettle_temp_c": 93},
    ]


@pytest.fixture
def experiment(client):
    equipment = client.post(
        "/equipment-sets",
        json={
            "name": "Set",
            "filter_label": "Paper",
            "brewer_label": "V60",
            "grinder_label": "Grinder",
            "grind_setting_unit": "click",
            "note": None,
        },
    )
    response = client.post(
        "/experiments",
        json={
            "title": "Bloom temperature",
            "hypothesis": "A 50 C bloom lowers TDS and EY",
            "changed_variable": "kettle temperature of the first pour",
            "bean_label": "Ethiopia Guji",
            "roast_date": "2026-10-28",
            "equipment_set_id": equipment.json()["id"],
            "extraction_style": "percolation",
            "planned_trials_per_condition": 1,
            "conditions": [
                {"label": "A", "name": "50 C bloom", "dose_g": 15, "steps": steps(50)},
                {"label": "B", "name": "93 C bloom", "dose_g": 15, "steps": steps(93)},
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    return {
        "id": body["id"],
        "A": body["conditions"][0]["id"],
        "B": body["conditions"][1]["id"],
    }


def trial_payload(**overrides):
    payload = {
        "brewed_at": "2026-11-05T08:30:00+09:00",
        "dose_g_actual": 15.02,
        "beverage_mass_g": 212.4,
        "brew_time_s": 210,
        "followed_plan": True,
        "tds_readings": [{"tds_pct": 1.38}, {"tds_pct": 1.40, "sample_temp_c": 25.5}],
        "sensory": {"overall_score": 7, "acidity": 3, "blinded": False},
    }
    payload.update(overrides)
    return payload


def create_trial(client, condition_id, **overrides):
    response = client.post(f"/conditions/{condition_id}/trials", json=trial_payload(**overrides))
    assert response.status_code == 201, response.json()
    return response.json()


def count(table):
    with database.get_connection() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- create and derived values ---------------------------------------------


def test_create_returns_measured_and_derived_values(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert trial["trial_no"] == 1
    assert trial["condition_label"] == "A"
    assert trial["experiment_id"] == experiment["id"]
    assert trial["brewed_at"].startswith("2026-11-04T23:30:00")  # stored as UTC
    assert [r["tds_pct"] for r in trial["measured"]["tds_readings"]] == [1.38, 1.40]
    assert trial["sensory"]["overall_score"] == 7

    derived = trial["derived"]
    assert derived["tds_mean_pct"] == {"value": pytest.approx(1.39), "n": 2}
    assert derived["tds_reading_sd_pct"]["value"] == pytest.approx(0.014142, abs=1e-6)
    assert derived["ey_pct"]["value"] == pytest.approx(19.656, abs=0.001)
    assert derived["ey_pct"]["method"] == "BEVERAGE_MASS_V1"
    assert derived["ey_pct"]["inputs"] == {
        "tds_mean_pct": pytest.approx(1.39),
        "beverage_mass_g": 212.4,
        "dose_g_actual": 15.02,
    }
    assert derived["ey_pct"]["null_reason"] is None
    assert derived["planned_total_water_g"] == 250


def test_days_since_roast_uses_the_local_date(client, experiment):
    # 2026-11-05 08:30 in Tokyo is still 2026-11-04 in UTC; the bag's roast date is local.
    trial = create_trial(client, experiment["A"])

    assert trial["derived"]["days_since_roast"] == 8


def test_minimal_trial_has_null_ey_with_reason(client, experiment):
    trial = create_trial(
        client, experiment["A"], beverage_mass_g=None, brew_time_s=None, tds_readings=[], sensory=None
    )

    assert trial["derived"]["ey_pct"]["value"] is None
    assert trial["derived"]["ey_pct"]["null_reason"] == "NO_TDS_READING"
    assert trial["derived"]["tds_reading_sd_pct"] == {"value": None, "n": 0}
    assert trial["sensory"] is None


def test_trial_numbers_count_per_condition(client, experiment):
    assert create_trial(client, experiment["A"])["trial_no"] == 1
    assert create_trial(client, experiment["B"])["trial_no"] == 1
    assert create_trial(client, experiment["A"])["trial_no"] == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"followed_plan": False},
        {"followed_plan": False, "deviation_note": "   "},
        {"excluded": True},
        {"brewed_at": "2026-11-05T08:30:00"},
        {"dose_g_actual": 15.023},
        {"tds_readings": [{"tds_pct": 1.385}]},
        {"tds_readings": [{"tds_pct": 1.4}] * 11},
        {"sensory": {"blinded": True}},
        {"sensory": {"acidity": 6, "blinded": True}},
    ],
)
def test_create_rejects_invalid_trial(client, experiment, overrides):
    response = client.post(f"/conditions/{experiment['A']}/trials", json=trial_payload(**overrides))

    assert response.status_code == 422
    assert count("trials") == 0


def test_create_for_missing_condition_returns_404(client):
    response = client.post("/conditions/999/trials", json=trial_payload())

    assert response.status_code == 404


def test_create_is_atomic(client, experiment, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(trial_repository, "upsert_sensory", fail)

    with pytest.raises(RuntimeError):
        client.post(f"/conditions/{experiment['A']}/trials", json=trial_payload())

    assert count("trials") == 0
    assert count("tds_readings") == 0


# ---- read / update / delete ------------------------------------------------


def test_get_and_missing(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert client.get(f"/trials/{trial['id']}").json()["id"] == trial["id"]
    assert client.get("/trials/999").status_code == 404


def test_patch_recomputes_derived_values(client, experiment):
    trial = create_trial(client, experiment["A"])

    response = client.patch(f"/trials/{trial['id']}", json={"beverage_mass_g": 220})

    assert response.status_code == 200
    assert response.json()["derived"]["ey_pct"]["value"] == pytest.approx(1.39 * 220 / 15.02)


def test_patch_null_clears_nullable_field(client, experiment):
    trial = create_trial(client, experiment["A"])

    response = client.patch(f"/trials/{trial['id']}", json={"beverage_mass_g": None})

    assert response.json()["measured"]["beverage_mass_g"] is None
    assert response.json()["derived"]["ey_pct"]["null_reason"] == "NO_BEVERAGE_MASS"


def test_patch_validates_the_merged_trial(client, experiment):
    trial = create_trial(client, experiment["A"])

    excluded = client.patch(f"/trials/{trial['id']}", json={"excluded": True})
    deviated = client.patch(f"/trials/{trial['id']}", json={"followed_plan": False})

    assert excluded.status_code == 422
    assert "exclusion_reason" in excluded.json()["detail"][0]["msg"]
    assert deviated.status_code == 422
    assert client.get(f"/trials/{trial['id']}").json()["excluded"] is False


def test_patch_can_exclude_with_reason(client, experiment):
    trial = create_trial(client, experiment["A"])

    response = client.patch(
        f"/trials/{trial['id']}", json={"excluded": True, "exclusion_reason": "spilled during pour"}
    )

    assert response.status_code == 200
    assert response.json()["excluded"] is True


def test_patch_empty_null_required_and_missing(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert client.patch(f"/trials/{trial['id']}", json={}).status_code == 400
    assert client.patch(f"/trials/{trial['id']}", json={"dose_g_actual": None}).status_code == 422
    assert client.patch("/trials/999", json={"note": "x"}).status_code == 404


def test_delete_cascades_and_unlocks_nothing_else(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert client.delete(f"/trials/{trial['id']}").status_code == 204
    assert client.get(f"/trials/{trial['id']}").status_code == 404
    assert count("tds_readings") == 0
    assert count("sensory_evaluations") == 0
    assert client.delete(f"/trials/{trial['id']}").status_code == 404


# ---- TDS readings ----------------------------------------------------------


def test_add_and_delete_tds_reading_changes_ey(client, experiment):
    trial = create_trial(client, experiment["A"], tds_readings=[])

    added = client.post(f"/trials/{trial['id']}/tds-readings", json={"tds_pct": 1.45})
    after_add = client.get(f"/trials/{trial['id']}").json()
    removed = client.delete(f"/tds-readings/{added.json()['id']}")
    after_remove = client.get(f"/trials/{trial['id']}").json()

    assert added.status_code == 201
    assert after_add["derived"]["ey_pct"]["value"] == pytest.approx(1.45 * 212.4 / 15.02)
    assert removed.status_code == 204
    assert after_remove["derived"]["ey_pct"]["null_reason"] == "NO_TDS_READING"


def test_tds_reading_limit_is_conflict(client, experiment):
    trial = create_trial(client, experiment["A"], tds_readings=[{"tds_pct": 1.4}] * 10)

    response = client.post(f"/trials/{trial['id']}/tds-readings", json={"tds_pct": 1.4})

    assert response.status_code == 409


def test_tds_reading_errors(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert client.post(f"/trials/{trial['id']}/tds-readings", json={"tds_pct": 0}).status_code == 422
    assert client.post("/trials/999/tds-readings", json={"tds_pct": 1.4}).status_code == 404
    assert client.delete("/tds-readings/999").status_code == 404


# ---- sensory evaluation ----------------------------------------------------


def test_put_sensory_creates_then_replaces(client, experiment):
    trial = create_trial(client, experiment["A"], sensory=None)

    created = client.put(f"/trials/{trial['id']}/sensory", json={"bitterness": 2, "blinded": True})
    replaced = client.put(f"/trials/{trial['id']}/sensory", json={"overall_score": 5, "blinded": True})

    assert created.status_code == 200
    assert created.json()["bitterness"] == 2
    assert replaced.json()["overall_score"] == 5
    assert replaced.json()["bitterness"] is None  # PUT replaces the whole evaluation
    assert count("sensory_evaluations") == 1


def test_sensory_errors_and_delete(client, experiment):
    trial = create_trial(client, experiment["A"])

    assert client.put(f"/trials/{trial['id']}/sensory", json={"blinded": True}).status_code == 422
    assert client.put("/trials/999/sensory", json={"overall_score": 5, "blinded": True}).status_code == 404
    assert client.delete(f"/trials/{trial['id']}/sensory").status_code == 204
    assert client.delete(f"/trials/{trial['id']}/sensory").status_code == 404


# ---- effect on the experiment ----------------------------------------------


def test_trials_drive_experiment_status_and_locks(client, experiment):
    create_trial(client, experiment["A"])

    running = client.get(f"/experiments/{experiment['id']}").json()
    locked = client.put(
        f"/conditions/{experiment['A']}/protocol", json={"dose_g": 16, "steps": steps(50)}
    )
    create_trial(client, experiment["B"], brewed_at="2026-11-05T09:30:00+09:00")
    reached = client.get(f"/experiments/{experiment['id']}").json()

    assert running["status"] == "RUNNING"
    assert running["next_condition_label"] == "B"
    assert locked.status_code == 409
    assert reached["status"] == "PLANNED_REACHED"
    assert reached["next_condition_label"] == "A"
