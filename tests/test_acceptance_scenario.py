"""01b 1.2 acceptance scenario, through the HTTP API only.

50 C bloom (A) vs 93 C bloom (B), 15 g dose, three trials each brewed
alternately, TDS read twice per beverage.
"""
import math

import pytest
from fastapi.testclient import TestClient

from app import db as database
from app.main import app


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


# (condition, TDS readings, beverage g, overall score, acidity)
BREWS = [
    ("A", [1.30, 1.32], 212, 6, 3),
    ("B", [1.40, 1.42], 210, 7, 4),
    ("A", [1.34, 1.34], 213, 7, 3),
    ("B", [1.44, 1.44], 211, 8, 3),
    ("A", [1.28, 1.30], 211, 6, 2),
    ("B", [1.38, 1.40], 212, 7, 4),
]


def sample_sd(values):
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def test_bloom_temperature_experiment_end_to_end(client):
    # 1. fixed beans/equipment, two conditions with timed steps
    equipment = client.post(
        "/equipment-sets",
        json={"name": "Home V60", "filter_label": "Paper", "brewer_label": "V60",
              "grinder_label": "Grinder", "grind_setting_unit": "click", "note": None},
    ).json()
    created = client.post(
        "/experiments",
        json={
            "title": "Bloom temperature",
            "hypothesis": "A 50 C bloom lowers TDS and EY",
            "changed_variable": "kettle temperature of the first pour",
            "bean_label": "Ethiopia Guji",
            "roast_date": "2026-10-28",
            "equipment_set_id": equipment["id"],
            "extraction_style": "percolation",
            "tds_device_label": "refractometer",
            "planned_trials_per_condition": 3,
            "conditions": [
                {"label": "A", "name": "50 C bloom", "dose_g": 15, "grind_setting_value": 20, "steps": steps(50)},
                {"label": "B", "name": "93 C bloom", "dose_g": 15, "grind_setting_value": 20, "steps": steps(93)},
            ],
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    condition_ids = {c["label"]: c["id"] for c in experiment["conditions"]}

    # 2. the plans differ in exactly one item
    assert experiment["condition_diff"]["items"] == [{"path": "steps[1].kettle_temp_c", "a": 50.0, "b": 93.0}]

    # 3. alternate A and B following the next-condition hint
    for hour, (label, readings, beverage, overall, acidity) in enumerate(BREWS):
        hint = client.get(f"/experiments/{experiment['id']}").json()["next_condition_label"]
        assert hint == label
        response = client.post(
            f"/conditions/{condition_ids[label]}/trials",
            json={
                "brewed_at": f"2026-11-05T{8 + hour:02d}:00:00+09:00",
                "dose_g_actual": 15.0,
                "beverage_mass_g": beverage,
                "brew_time_s": 200,
                "followed_plan": True,
                "tds_readings": [{"tds_pct": value} for value in readings],
                "sensory": {"overall_score": overall, "acidity": acidity, "blinded": True},
            },
        )
        assert response.status_code == 201

    assert client.get(f"/experiments/{experiment['id']}").json()["status"] == "PLANNED_REACHED"

    # 4. and 5. compare TDS, EY and sensory with both kinds of spread
    comparison = client.get(f"/experiments/{experiment['id']}/comparison")
    assert comparison.status_code == 200
    body = comparison.json()
    a, b = body["conditions"]
    assert (a["label"], b["label"]) == ("A", "B")

    a_tds, b_tds = [1.31, 1.34, 1.29], [1.41, 1.44, 1.39]
    assert [v["value"] for v in a["metrics"]["tds_pct"]["values"]] == pytest.approx(a_tds)
    assert a["metrics"]["tds_pct"]["n"] == 3
    assert a["metrics"]["tds_pct"]["mean"] == pytest.approx(sum(a_tds) / 3)
    assert a["metrics"]["tds_pct"]["sd"] == pytest.approx(sample_sd(a_tds))
    assert a["metrics"]["tds_pct"]["median"] == pytest.approx(1.31)
    assert body["differences"]["tds_pct"]["mean_b_minus_a"] == pytest.approx(0.10)

    a_ey = [1.31 * 212 / 15, 1.34 * 213 / 15, 1.29 * 211 / 15]
    b_ey = [1.41 * 210 / 15, 1.44 * 211 / 15, 1.39 * 212 / 15]
    assert b["metrics"]["ey_pct"]["values"][0]["value"] == pytest.approx(b_ey[0])
    assert body["differences"]["ey_pct"]["mean_b_minus_a"] == pytest.approx(sum(b_ey) / 3 - sum(a_ey) / 3)

    assert a["metrics"]["overall_score"]["median"] == 6
    assert b["metrics"]["overall_score"]["median"] == 7
    assert b["metrics"]["acidity"]["max"] == 4

    for label in ("A", "B"):
        variability = body["tds_variability"][label]
        assert variability["measurement_sd"]["value"] == pytest.approx(math.sqrt(0.0004 / 3))
        assert variability["between_trial_sd"]["value"] == pytest.approx(sample_sd(a_tds))

    assert body["warnings"] == [{"code": "N_SMALL", "count": None}]

    # 6. the plan is locked once trials exist
    locked = client.put(
        f"/conditions/{condition_ids['A']}/protocol",
        json={"dose_g": 15, "grind_setting_value": 20, "steps": steps(60)},
    )
    assert locked.status_code == 409


def test_comparison_default_omits_deviated_trials(client):
    equipment = client.post(
        "/equipment-sets",
        json={"name": "S", "filter_label": "P", "brewer_label": "V60",
              "grinder_label": "G", "grind_setting_unit": "click", "note": None},
    ).json()
    experiment = client.post(
        "/experiments",
        json={
            "title": "t", "hypothesis": "h", "changed_variable": "v", "bean_label": "b",
            "equipment_set_id": equipment["id"], "extraction_style": "immersion",
            "planned_trials_per_condition": 3,
            "conditions": [
                {"label": "A", "name": "a", "dose_g": 15, "steps": steps(50)},
                {"label": "B", "name": "b", "dose_g": 15, "steps": steps(93)},
            ],
        },
    ).json()
    condition_b = experiment["conditions"][1]["id"]
    client.post(
        f"/conditions/{condition_b}/trials",
        json={"brewed_at": "2026-11-05T08:00:00+09:00", "dose_g_actual": 15, "followed_plan": False,
              "deviation_note": "poured too fast", "tds_readings": [{"tds_pct": 1.5}]},
    )

    default = client.get(f"/experiments/{experiment['id']}/comparison").json()
    with_deviated = client.get(f"/experiments/{experiment['id']}/comparison?include_deviated=true").json()

    assert default["conditions"][1]["included_trial_count"] == 0
    assert {"code": "DEVIATED_OR_EXCLUDED", "count": 1} in default["warnings"]
    assert {"code": "EY_METHOD_ASSUMPTION", "count": None} in default["warnings"]
    assert with_deviated["include_deviated"] is True
    assert with_deviated["conditions"][1]["included_trial_count"] == 1
    assert with_deviated["differences"]["tds_pct"]["mean_b_minus_a"] is None  # A has no trials
    assert client.get("/experiments/999/comparison").status_code == 404
