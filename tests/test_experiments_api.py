import pytest
from fastapi.testclient import TestClient

from app import db as database
from app.main import app
from app.repositories import experiments as experiment_repository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    with TestClient(app) as test_client:
        yield test_client


def create_equipment_set(client):
    response = client.post(
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
    assert response.status_code == 201
    return response.json()["id"]


def steps(first_pour_temp):
    """Acceptance scenario (01b 1.2): only the first pour's kettle temperature differs."""
    return [
        {"step_type": "pour", "start_s": 0, "water_g": 30, "kettle_temp_c": first_pour_temp},
        {"step_type": "pour", "start_s": 120, "water_g": 100, "kettle_temp_c": 93},
        {"step_type": "pour", "start_s": 150, "water_g": 120, "kettle_temp_c": 93},
    ]


def experiment_payload(equipment_set_id, **overrides):
    payload = {
        "title": "Bloom temperature",
        "hypothesis": "A 50 C bloom lowers TDS and EY",
        "changed_variable": "kettle temperature of the first pour",
        "bean_label": "Ethiopia Guji",
        "roast_date": "2026-10-28",
        "equipment_set_id": equipment_set_id,
        "extraction_style": "percolation",
        "planned_trials_per_condition": 3,
        "conditions": [
            {"label": "A", "name": "50 C bloom", "dose_g": 15, "grind_setting_value": 20, "steps": steps(50)},
            {"label": "B", "name": "93 C bloom", "dose_g": 15, "grind_setting_value": 20, "steps": steps(93)},
        ],
    }
    payload.update(overrides)
    return payload


def create_experiment(client, **overrides):
    response = client.post("/experiments", json=experiment_payload(create_equipment_set(client), **overrides))
    assert response.status_code == 201, response.json()
    return response.json()


def add_trial(condition_id, trial_no=1, brewed_at="2026-11-05T00:00:00+00:00"):
    """Trials have no API until PR6; insert directly to exercise the locks."""
    with database.get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trials (condition_id, trial_no, brewed_at, dose_g_actual, beverage_mass_g, followed_plan)
            VALUES (?, ?, ?, 15.02, 212.4, 1)
            """,
            (condition_id, trial_no, brewed_at),
        )
        trial_id = cursor.lastrowid
        conn.execute("INSERT INTO tds_readings (trial_id, tds_pct) VALUES (?, 1.38), (?, 1.40)", (trial_id, trial_id))
        conn.execute("INSERT INTO sensory_evaluations (trial_id, overall_score, blinded) VALUES (?, 7, 0)", (trial_id,))
    return trial_id


def condition_id(experiment, label):
    return next(c["id"] for c in experiment["conditions"] if c["label"] == label)


# ---- create ----------------------------------------------------------------


def test_create_returns_plan_diff_and_derived_state(client):
    experiment = create_experiment(client)

    assert experiment["status"] == "DRAFT"
    assert experiment["next_condition_label"] == "A"
    assert experiment["ey_method"] == "BEVERAGE_MASS_V1"
    assert experiment["equipment_set_name_snapshot"] == "Set"
    assert experiment["condition_diff"] == {
        "items": [{"path": "steps[1].kettle_temp_c", "a": 50.0, "b": 93.0}],
        "count": 1,
    }
    condition_a = experiment["conditions"][0]
    assert condition_a["label"] == "A"
    assert condition_a["planned_total_water_g"] == 250
    assert [step["seq"] for step in condition_a["steps"]] == [1, 2, 3]
    assert experiment["trials"] == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"conditions": []},
        {"extraction_style": "espresso"},
        {"planned_trials_per_condition": 0},
        {"title": "   "},
    ],
)
def test_create_rejects_invalid_experiment(client, overrides):
    response = client.post("/experiments", json=experiment_payload(create_equipment_set(client), **overrides))

    assert response.status_code == 422


def test_create_requires_one_a_and_one_b(client):
    payload = experiment_payload(create_equipment_set(client))
    payload["conditions"][1]["label"] = "A"

    assert client.post("/experiments", json=payload).status_code == 422


@pytest.mark.parametrize(
    "bad_steps",
    [
        [{"step_type": "pour", "start_s": 5, "water_g": 30, "kettle_temp_c": 93}],
        [{"step_type": "pour", "start_s": 0, "water_g": 30.123, "kettle_temp_c": 93}],
        [{"step_type": "pour", "start_s": 0, "water_g": 30, "kettle_temp_c": 93.25}],
        [{"step_type": "agitate", "start_s": 0, "agitation_method": "stir"}],
        [{"step_type": "wait", "start_s": 0}],
    ],
)
def test_create_rejects_invalid_steps(client, bad_steps):
    payload = experiment_payload(create_equipment_set(client))
    payload["conditions"][1]["steps"] = bad_steps

    assert client.post("/experiments", json=payload).status_code == 422


def test_create_with_inactive_equipment_set_returns_404(client):
    equipment_set_id = create_equipment_set(client)
    client.delete(f"/equipment-sets/{equipment_set_id}")

    response = client.post("/experiments", json=experiment_payload(equipment_set_id))

    assert response.status_code == 404


def test_create_is_atomic(client, monkeypatch):
    original = experiment_repository.insert_steps
    calls = {"n": 0}

    def fail_on_second_condition(conn, condition_id, rows):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated failure")
        original(conn, condition_id, rows)

    monkeypatch.setattr(experiment_repository, "insert_steps", fail_on_second_condition)
    equipment_set_id = create_equipment_set(client)

    with pytest.raises(RuntimeError):
        client.post("/experiments", json=experiment_payload(equipment_set_id))

    with database.get_connection() as conn:
        for table in ("experiments", "conditions", "protocol_steps"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table


# ---- read ------------------------------------------------------------------


def test_get_and_list(client):
    experiment = create_experiment(client)

    assert client.get(f"/experiments/{experiment['id']}").json()["title"] == "Bloom temperature"
    listed = client.get("/experiments").json()
    assert listed == [
        {
            "id": experiment["id"],
            "title": "Bloom temperature",
            "bean_label": "Ethiopia Guji",
            "created_at": experiment["created_at"],
            "status": "DRAFT",
            "trial_counts": {"A": 0, "B": 0},
        }
    ]
    assert client.get("/experiments/999").status_code == 404


def test_detail_includes_trial_summary_and_next_condition(client):
    experiment = create_experiment(client)
    add_trial(condition_id(experiment, "A"))

    detail = client.get(f"/experiments/{experiment['id']}").json()

    assert detail["status"] == "RUNNING"
    assert detail["next_condition_label"] == "B"
    trial = detail["trials"][0]
    assert trial["condition_label"] == "A"
    assert trial["tds_mean_pct"] == pytest.approx(1.39)
    assert trial["ey_pct"] == pytest.approx(19.656, abs=0.001)
    assert trial["overall_score"] == 7


# ---- update / delete ---------------------------------------------------------


def test_patch_text_fields(client):
    experiment = create_experiment(client)

    response = client.patch(
        f"/experiments/{experiment['id']}",
        json={"title": "Renamed", "fixed_conditions_note": "dripper preheated"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert response.json()["fixed_conditions_note"] == "dripper preheated"


def test_patch_empty_and_null_required(client):
    experiment = create_experiment(client)

    assert client.patch(f"/experiments/{experiment['id']}", json={}).status_code == 400
    assert client.patch(f"/experiments/{experiment['id']}", json={"title": None}).status_code == 422


def test_fixed_conditions_change_freely_before_trials(client):
    experiment = create_experiment(client)
    other_set = create_equipment_set(client)

    response = client.patch(
        f"/experiments/{experiment['id']}",
        json={"bean_label": "Kenya", "equipment_set_id": other_set, "water_label": "soft"},
    )

    assert response.status_code == 200
    assert response.json()["bean_label"] == "Kenya"
    assert response.json()["equipment_set_id"] == other_set


@pytest.mark.parametrize(
    "patch",
    [
        {"bean_label": "Kenya"},
        {"roast_date": "2026-10-30"},
        {"extraction_style": "immersion"},
        {"water_label": "hard"},
        {"tds_device_label": "another meter"},
    ],
)
def test_fixed_conditions_are_locked_after_trials(client, patch):
    experiment = create_experiment(client)
    add_trial(condition_id(experiment, "A"))

    response = client.patch(f"/experiments/{experiment['id']}", json=patch)

    assert response.status_code == 409


def test_unchanged_fixed_values_and_free_fields_are_allowed_after_trials(client):
    experiment = create_experiment(client)
    add_trial(condition_id(experiment, "A"))

    response = client.patch(
        f"/experiments/{experiment['id']}",
        json={"bean_label": "Ethiopia Guji", "roast_date": "2026-10-28", "hypothesis": "revised"},
    )

    assert response.status_code == 200
    assert response.json()["hypothesis"] == "revised"


def test_delete_without_trials(client):
    experiment = create_experiment(client)

    assert client.delete(f"/experiments/{experiment['id']}").status_code == 204
    assert client.get(f"/experiments/{experiment['id']}").status_code == 404
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM protocol_steps").fetchone()[0] == 0


def test_delete_with_trials_is_conflict(client):
    experiment = create_experiment(client)
    add_trial(condition_id(experiment, "A"))

    assert client.delete(f"/experiments/{experiment['id']}").status_code == 409
    assert client.delete("/experiments/999").status_code == 404


# ---- conditions ----------------------------------------------------------------


def test_patch_condition_name_and_note(client):
    experiment = create_experiment(client)

    response = client.patch(f"/conditions/{condition_id(experiment, 'A')}", json={"name": "Cool bloom", "note": "n"})

    assert response.status_code == 200
    assert response.json()["name"] == "Cool bloom"
    assert client.patch(f"/conditions/{condition_id(experiment, 'A')}", json={}).status_code == 400
    assert client.patch("/conditions/999", json={"name": "x"}).status_code == 404


def test_replace_protocol_before_trials_updates_plan_and_diff(client):
    experiment = create_experiment(client)
    target = condition_id(experiment, "B")

    response = client.put(
        f"/conditions/{target}/protocol",
        json={"dose_g": 16, "grind_setting_value": 20, "steps": steps(50)},
    )

    assert response.status_code == 200
    assert response.json()["dose_g"] == 16
    detail = client.get(f"/experiments/{experiment['id']}").json()
    assert detail["condition_diff"]["items"] == [{"path": "dose_g", "a": 15.0, "b": 16.0}]


def test_replace_protocol_is_locked_after_trials(client):
    experiment = create_experiment(client)
    target = condition_id(experiment, "A")
    add_trial(target)

    response = client.put(
        f"/conditions/{target}/protocol",
        json={"dose_g": 15, "grind_setting_value": 20, "steps": steps(60)},
    )

    assert response.status_code == 409


def test_replace_protocol_validates_steps(client):
    experiment = create_experiment(client)

    response = client.put(
        f"/conditions/{condition_id(experiment, 'A')}/protocol",
        json={"dose_g": 15, "steps": [{"step_type": "pour", "start_s": 10, "water_g": 30, "kettle_temp_c": 93}]},
    )

    assert response.status_code == 422


# ---- failure paths: nothing changes when a request is refused ------------------


def plan_of(client, experiment_id, label):
    detail = client.get(f"/experiments/{experiment_id}").json()
    condition = next(c for c in detail["conditions"] if c["label"] == label)
    return {key: condition[key] for key in ("dose_g", "grind_setting_value", "steps")}


def test_replace_protocol_rolls_back_to_the_old_plan_on_failure(client, monkeypatch):
    """The old steps are deleted before the new ones are inserted; a failure
    in between must restore the old plan, not leave a condition without steps."""
    experiment = create_experiment(client)
    target = condition_id(experiment, "A")
    before = plan_of(client, experiment["id"], "A")
    original = experiment_repository.insert_steps

    def fail(conn, condition_id, rows):
        raise RuntimeError("simulated failure after the old steps were deleted")

    monkeypatch.setattr(experiment_repository, "insert_steps", fail)
    with pytest.raises(RuntimeError):
        client.put(f"/conditions/{target}/protocol", json={"dose_g": 16, "grind_setting_value": 25, "steps": steps(60)})
    monkeypatch.setattr(experiment_repository, "insert_steps", original)

    assert plan_of(client, experiment["id"], "A") == before
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM protocol_steps WHERE condition_id = ?", (target,)).fetchone()[0] == 3


def test_refused_plan_and_fixed_condition_changes_leave_data_unchanged(client):
    experiment = create_experiment(client)
    target = condition_id(experiment, "A")
    add_trial(target)
    before = client.get(f"/experiments/{experiment['id']}").json()

    protocol = client.put(f"/conditions/{target}/protocol", json={"dose_g": 16, "steps": steps(60)})
    fixed = client.patch(f"/experiments/{experiment['id']}", json={"bean_label": "Kenya", "title": "renamed"})
    deleted = client.delete(f"/experiments/{experiment['id']}")

    assert (protocol.status_code, fixed.status_code, deleted.status_code) == (409, 409, 409)
    after = client.get(f"/experiments/{experiment['id']}").json()
    assert after == before  # the free field in the same PATCH was not applied either


def test_equipment_set_is_a_fixed_condition_after_trials(client):
    experiment = create_experiment(client)
    other_set = create_equipment_set(client)
    add_trial(condition_id(experiment, "A"))

    response = client.patch(f"/experiments/{experiment['id']}", json={"equipment_set_id": other_set})

    assert response.status_code == 409
    assert client.get(f"/experiments/{experiment['id']}").json()["equipment_set_id"] == experiment["equipment_set_id"]


def test_patch_to_missing_or_hidden_equipment_set_returns_404(client):
    experiment = create_experiment(client)
    hidden_set = create_equipment_set(client)
    assert client.delete(f"/equipment-sets/{hidden_set}").status_code == 200

    hidden = client.patch(f"/experiments/{experiment['id']}", json={"equipment_set_id": hidden_set})
    missing = client.patch(f"/experiments/{experiment['id']}", json={"equipment_set_id": 999})

    assert (hidden.status_code, missing.status_code) == (404, 404)
    assert client.get(f"/experiments/{experiment['id']}").json()["equipment_set_id"] == experiment["equipment_set_id"]


def test_missing_resources_return_404(client):
    assert client.patch("/experiments/999", json={"title": "x"}).status_code == 404
    assert client.put("/conditions/999/protocol", json={"dose_g": 15, "steps": steps(93)}).status_code == 404


@pytest.mark.parametrize("patch", [{"name": None}, {"name": "   "}])
def test_patch_condition_rejects_blank_or_null_name(client, patch):
    experiment = create_experiment(client)

    response = client.patch(f"/conditions/{condition_id(experiment, 'A')}", json=patch)

    assert response.status_code == 422
    assert client.get(f"/experiments/{experiment['id']}").json()["conditions"][0]["name"] == "50 C bloom"


def test_error_bodies_follow_the_documented_shape(client):
    """README: 400 / 404 / 409 carry a string detail; 422 carries a list of
    {loc, msg, type} for request validation and merge validation alike."""
    experiment = create_experiment(client)
    add_trial(condition_id(experiment, "A"))

    empty = client.patch(f"/experiments/{experiment['id']}", json={})
    missing = client.get("/experiments/999")
    conflict = client.delete(f"/experiments/{experiment['id']}")
    invalid = client.patch(f"/experiments/{experiment['id']}", json={"planned_trials_per_condition": 0})

    for response, status in ((empty, 400), (missing, 404), (conflict, 409)):
        assert response.status_code == status
        assert isinstance(response.json()["detail"], str)
    assert invalid.status_code == 422
    assert {"loc", "msg", "type"} <= set(invalid.json()["detail"][0])
