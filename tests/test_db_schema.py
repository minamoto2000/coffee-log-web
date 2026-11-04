"""DB constraints of the redesigned schema (01b section 6), checked with raw SQL.

The request schema validates the same rules first; these tests make sure
invalid rows cannot be written even if a code path skips that validation.
"""
import sqlite3

import pytest

from app import db as database


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    connection = database.get_connection()
    yield connection
    connection.close()


def insert(conn, table, **values):
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    cursor = conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values())
    )
    return cursor.lastrowid


def make_experiment(conn, **overrides):
    equipment_set_id = insert(
        conn,
        "equipment_sets",
        name="Set",
        filter_label="Paper",
        brewer_label="V60",
        grinder_label="Grinder",
        grind_setting_unit="click",
    )
    values = dict(
        title="Bloom temperature",
        hypothesis="Lower bloom temperature lowers TDS",
        changed_variable="kettle temperature of the first pour",
        bean_label="Ethiopia",
        equipment_set_id=equipment_set_id,
        equipment_set_name_snapshot="Set",
        brewer_label_snapshot="V60",
        filter_label_snapshot="Paper",
        grinder_label_snapshot="Grinder",
        grind_setting_unit_snapshot="click",
        extraction_style="percolation",
        planned_trials_per_condition=3,
    )
    values.update(overrides)
    return insert(conn, "experiments", **values)


def make_condition(conn, experiment_id, label="A"):
    return insert(conn, "conditions", experiment_id=experiment_id, label=label, name=label, dose_g=15)


def pour(conn, condition_id, seq=1, **overrides):
    values = dict(
        condition_id=condition_id, seq=seq, step_type="pour", start_s=0, water_g=30, kettle_temp_c=93
    )
    values.update(overrides)
    return insert(conn, "protocol_steps", **values)


def make_trial(conn, condition_id, trial_no=1, **overrides):
    values = dict(
        condition_id=condition_id,
        trial_no=trial_no,
        brewed_at="2026-11-05T00:00:00+00:00",
        dose_g_actual=15.02,
        followed_plan=1,
    )
    values.update(overrides)
    return insert(conn, "trials", **values)


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_init_db_is_idempotent(conn):
    database.init_db()

    assert count(conn, "experiments") == 0


def test_valid_rows_are_accepted(conn):
    condition_id = make_condition(conn, make_experiment(conn))
    pour(conn, condition_id, seq=1)
    insert(conn, "protocol_steps", condition_id=condition_id, seq=2, step_type="agitate",
           start_s=10, agitation_method="stir")
    insert(conn, "protocol_steps", condition_id=condition_id, seq=3, step_type="other",
           start_s=20, label="open valve")
    trial_id = make_trial(conn, condition_id)
    insert(conn, "tds_readings", trial_id=trial_id, tds_pct=1.38, sample_temp_c=25.0)
    insert(conn, "sensory_evaluations", trial_id=trial_id, overall_score=7, blinded=0)

    assert count(conn, "protocol_steps") == 3


def test_ey_method_defaults_and_is_restricted(conn):
    experiment_id = make_experiment(conn)
    method = conn.execute("SELECT ey_method FROM experiments WHERE id = ?", (experiment_id,)).fetchone()[0]

    assert method == "BEVERAGE_MASS_V1"
    with pytest.raises(sqlite3.IntegrityError):
        make_experiment(conn, ey_method="TOTAL_WATER_V1")


@pytest.mark.parametrize(
    "overrides",
    [
        {"extraction_style": "espresso"},
        {"planned_trials_per_condition": 0},
        {"planned_trials_per_condition": 21},
        {"title": "   "},
    ],
)
def test_invalid_experiment_values_are_rejected(conn, overrides):
    with pytest.raises(sqlite3.IntegrityError):
        make_experiment(conn, **overrides)


def test_condition_labels_are_a_or_b_and_unique(conn):
    experiment_id = make_experiment(conn)
    make_condition(conn, experiment_id, "A")

    with pytest.raises(sqlite3.IntegrityError):
        make_condition(conn, experiment_id, "A")
    with pytest.raises(sqlite3.IntegrityError):
        make_condition(conn, experiment_id, "C")


@pytest.mark.parametrize(
    "overrides",
    [
        {"kettle_temp_c": None},
        {"water_g": None},
        {"water_g": 0},
        {"kettle_temp_c": 101},
        {"label": "extra"},
        {"step_type": "wait"},
        {"start_s": -1},
    ],
)
def test_invalid_pour_rows_are_rejected(conn, overrides):
    condition_id = make_condition(conn, make_experiment(conn))

    with pytest.raises(sqlite3.IntegrityError):
        pour(conn, condition_id, **overrides)


@pytest.mark.parametrize(
    "values",
    [
        {"step_type": "agitate"},
        {"step_type": "agitate", "agitation_method": "shake"},
        {"step_type": "agitate", "agitation_method": "stir", "water_g": 10},
        {"step_type": "other"},
        {"step_type": "other", "label": "  "},
        {"step_type": "other", "label": "open valve", "kettle_temp_c": 90},
    ],
)
def test_type_specific_step_fields_are_enforced(conn, values):
    condition_id = make_condition(conn, make_experiment(conn))

    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "protocol_steps", condition_id=condition_id, seq=1, start_s=0, **values)


def test_step_seq_is_unique_per_condition(conn):
    condition_id = make_condition(conn, make_experiment(conn))
    pour(conn, condition_id, seq=1)

    with pytest.raises(sqlite3.IntegrityError):
        pour(conn, condition_id, seq=1, start_s=60)


@pytest.mark.parametrize(
    "overrides",
    [
        {"followed_plan": 0},
        {"followed_plan": 0, "deviation_note": " "},
        {"excluded": 1},
        {"dose_g_actual": 0},
        {"beverage_mass_g": 0},
        {"followed_plan": 2},
    ],
)
def test_invalid_trial_rows_are_rejected(conn, overrides):
    condition_id = make_condition(conn, make_experiment(conn))

    with pytest.raises(sqlite3.IntegrityError):
        make_trial(conn, condition_id, **overrides)


def test_deviation_and_exclusion_with_reasons_are_accepted(conn):
    condition_id = make_condition(conn, make_experiment(conn))

    make_trial(conn, condition_id, followed_plan=0, deviation_note="poured too fast",
               excluded=1, exclusion_reason="spilled")

    assert count(conn, "trials") == 1


def test_trial_no_is_unique_per_condition(conn):
    condition_id = make_condition(conn, make_experiment(conn))
    make_trial(conn, condition_id, trial_no=1)

    with pytest.raises(sqlite3.IntegrityError):
        make_trial(conn, condition_id, trial_no=1)


def test_trial_requires_existing_condition(conn):
    with pytest.raises(sqlite3.IntegrityError):
        make_trial(conn, condition_id=999)


@pytest.mark.parametrize("tds_pct", [0, -0.1, 30.01])
def test_tds_reading_range(conn, tds_pct):
    trial_id = make_trial(conn, make_condition(conn, make_experiment(conn)))

    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "tds_readings", trial_id=trial_id, tds_pct=tds_pct)


def test_sensory_evaluation_rules(conn):
    trial_id = make_trial(conn, make_condition(conn, make_experiment(conn)))

    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "sensory_evaluations", trial_id=trial_id, blinded=0)  # nothing rated
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "sensory_evaluations", trial_id=trial_id, acidity=6, blinded=0)
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "sensory_evaluations", trial_id=trial_id, overall_score=11, blinded=0)

    insert(conn, "sensory_evaluations", trial_id=trial_id, acidity=0, blinded=1)
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, "sensory_evaluations", trial_id=trial_id, overall_score=7, blinded=1)


def test_deleting_experiment_without_trials_cascades(conn):
    experiment_id = make_experiment(conn)
    pour(conn, make_condition(conn, experiment_id, "A"))
    pour(conn, make_condition(conn, experiment_id, "B"))

    conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))

    assert count(conn, "conditions") == 0
    assert count(conn, "protocol_steps") == 0


def test_deleting_experiment_with_trials_is_blocked(conn):
    experiment_id = make_experiment(conn)
    make_trial(conn, make_condition(conn, experiment_id))

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))


def test_deleting_trial_cascades_to_readings_and_sensory(conn):
    trial_id = make_trial(conn, make_condition(conn, make_experiment(conn)))
    insert(conn, "tds_readings", trial_id=trial_id, tds_pct=1.38)
    insert(conn, "tds_readings", trial_id=trial_id, tds_pct=1.40)
    insert(conn, "sensory_evaluations", trial_id=trial_id, overall_score=7, blinded=0)

    conn.execute("DELETE FROM trials WHERE id = ?", (trial_id,))

    assert count(conn, "tds_readings") == 0
    assert count(conn, "sensory_evaluations") == 0
