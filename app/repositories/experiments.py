"""SQL for experiments, conditions and protocol steps.

Functions take a connection and never commit: the service decides the
transaction boundary.
"""
import sqlite3

EXPERIMENT_UPDATABLE = (
    "title",
    "hypothesis",
    "changed_variable",
    "bean_label",
    "roast_date",
    "equipment_set_id",
    "equipment_set_name_snapshot",
    "brewer_label_snapshot",
    "filter_label_snapshot",
    "grinder_label_snapshot",
    "grind_setting_unit_snapshot",
    "extraction_style",
    "water_label",
    "tds_device_label",
    "fixed_conditions_note",
    "planned_trials_per_condition",
)
CONDITION_UPDATABLE = ("name", "note", "dose_g", "grind_setting_value")


def _update(conn: sqlite3.Connection, table: str, allowed: tuple[str, ...], row_id: int, updates: dict) -> None:
    unknown = set(updates) - set(allowed)
    if unknown:
        raise ValueError(f"not updatable: {sorted(unknown)}")
    columns = [column for column in allowed if column in updates]
    if not columns:
        return
    set_clause = ", ".join(f"{column} = ?" for column in columns)
    conn.execute(
        f"UPDATE {table} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*[updates[column] for column in columns], row_id),
    )


# ---- experiments -----------------------------------------------------------


def insert_experiment(conn: sqlite3.Connection, values: dict) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    cursor = conn.execute(
        f"INSERT INTO experiments ({columns}) VALUES ({placeholders})", tuple(values.values())
    )
    return cursor.lastrowid


def find_experiment(conn: sqlite3.Connection, experiment_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()


def list_experiments(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM experiments ORDER BY created_at DESC, id DESC").fetchall()


def update_experiment(conn: sqlite3.Connection, experiment_id: int, updates: dict) -> None:
    _update(conn, "experiments", EXPERIMENT_UPDATABLE, experiment_id, updates)


def delete_experiment(conn: sqlite3.Connection, experiment_id: int) -> None:
    conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))


def count_trials_for_experiment(conn: sqlite3.Connection, experiment_id: int) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) FROM trials
        JOIN conditions ON conditions.id = trials.condition_id
        WHERE conditions.experiment_id = ?
        """,
        (experiment_id,),
    ).fetchone()[0]


# ---- conditions and steps --------------------------------------------------


def insert_condition(conn: sqlite3.Connection, experiment_id: int, values: dict) -> int:
    cursor = conn.execute(
        """
        INSERT INTO conditions (experiment_id, label, name, dose_g, grind_setting_value, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_id,
            values["label"],
            values["name"],
            values["dose_g"],
            values["grind_setting_value"],
            values["note"],
        ),
    )
    return cursor.lastrowid


def find_condition(conn: sqlite3.Connection, condition_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM conditions WHERE id = ?", (condition_id,)).fetchone()


def list_conditions(conn: sqlite3.Connection, experiment_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM conditions WHERE experiment_id = ? ORDER BY label", (experiment_id,)
    ).fetchall()


def update_condition(conn: sqlite3.Connection, condition_id: int, updates: dict) -> None:
    _update(conn, "conditions", CONDITION_UPDATABLE, condition_id, updates)


def count_trials_for_condition(conn: sqlite3.Connection, condition_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM trials WHERE condition_id = ?", (condition_id,)
    ).fetchone()[0]


def insert_steps(conn: sqlite3.Connection, condition_id: int, steps: list[dict]) -> None:
    """seq is assigned from list order, starting at 1."""
    conn.executemany(
        """
        INSERT INTO protocol_steps (
            condition_id, seq, step_type, start_s, duration_s,
            water_g, kettle_temp_c, agitation_method, label, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                condition_id,
                seq,
                step["step_type"],
                step["start_s"],
                step["duration_s"],
                step["water_g"],
                step["kettle_temp_c"],
                step["agitation_method"],
                step["label"],
                step["note"],
            )
            for seq, step in enumerate(steps, start=1)
        ],
    )


def delete_steps(conn: sqlite3.Connection, condition_id: int) -> None:
    conn.execute("DELETE FROM protocol_steps WHERE condition_id = ?", (condition_id,))


def list_steps(conn: sqlite3.Connection, condition_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM protocol_steps WHERE condition_id = ? ORDER BY seq", (condition_id,)
    ).fetchall()


# ---- trial data needed for experiment-level derived values -----------------


def list_trials_for_experiment(conn: sqlite3.Connection, experiment_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT trials.*, conditions.label AS condition_label
        FROM trials
        JOIN conditions ON conditions.id = trials.condition_id
        WHERE conditions.experiment_id = ?
        ORDER BY trials.brewed_at, trials.id
        """,
        (experiment_id,),
    ).fetchall()


def tds_readings_by_trial(conn: sqlite3.Connection, trial_ids: list[int]) -> dict[int, list[float]]:
    readings: dict[int, list[float]] = {trial_id: [] for trial_id in trial_ids}
    if not trial_ids:
        return readings
    placeholders = ", ".join("?" for _ in trial_ids)
    rows = conn.execute(
        f"SELECT trial_id, tds_pct FROM tds_readings WHERE trial_id IN ({placeholders}) ORDER BY id",
        trial_ids,
    ).fetchall()
    for row in rows:
        readings[row["trial_id"]].append(row["tds_pct"])
    return readings


def overall_scores_by_trial(conn: sqlite3.Connection, trial_ids: list[int]) -> dict[int, int | None]:
    if not trial_ids:
        return {}
    placeholders = ", ".join("?" for _ in trial_ids)
    rows = conn.execute(
        f"SELECT trial_id, overall_score FROM sensory_evaluations WHERE trial_id IN ({placeholders})",
        trial_ids,
    ).fetchall()
    return {row["trial_id"]: row["overall_score"] for row in rows}


def sensory_by_trial(conn: sqlite3.Connection, trial_ids: list[int]) -> dict[int, sqlite3.Row]:
    if not trial_ids:
        return {}
    placeholders = ", ".join("?" for _ in trial_ids)
    rows = conn.execute(
        f"SELECT * FROM sensory_evaluations WHERE trial_id IN ({placeholders})", trial_ids
    ).fetchall()
    return {row["trial_id"]: row for row in rows}
