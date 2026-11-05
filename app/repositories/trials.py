"""SQL for trials, TDS readings and sensory evaluations. Never commits."""
import sqlite3

TRIAL_UPDATABLE = (
    "brewed_at",
    "dose_g_actual",
    "beverage_mass_g",
    "brew_time_s",
    "followed_plan",
    "deviation_note",
    "excluded",
    "exclusion_reason",
    "note",
)
SENSORY_COLUMNS = (
    "overall_score",
    "acidity",
    "sweetness",
    "bitterness",
    "body",
    "aroma",
    "blinded",
    "note",
)


# ---- trials ----------------------------------------------------------------


def next_trial_no(conn: sqlite3.Connection, condition_id: int) -> int:
    """Max + 1 within the condition. Call inside a write transaction so two
    inserts cannot read the same max."""
    return conn.execute(
        "SELECT COALESCE(MAX(trial_no), 0) + 1 FROM trials WHERE condition_id = ?", (condition_id,)
    ).fetchone()[0]


def insert_trial(conn: sqlite3.Connection, condition_id: int, trial_no: int, values: dict) -> int:
    cursor = conn.execute(
        """
        INSERT INTO trials (
            condition_id, trial_no, brewed_at, dose_g_actual, beverage_mass_g, brew_time_s,
            followed_plan, deviation_note, excluded, exclusion_reason, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (condition_id, trial_no, *(values[column] for column in TRIAL_UPDATABLE)),
    )
    return cursor.lastrowid


def find_trial(conn: sqlite3.Connection, trial_id: int) -> sqlite3.Row | None:
    """Trial with the context its derived values need."""
    return conn.execute(
        """
        SELECT trials.*,
               conditions.label AS condition_label,
               conditions.experiment_id AS experiment_id,
               experiments.roast_date AS roast_date
        FROM trials
        JOIN conditions ON conditions.id = trials.condition_id
        JOIN experiments ON experiments.id = conditions.experiment_id
        WHERE trials.id = ?
        """,
        (trial_id,),
    ).fetchone()


def update_trial(conn: sqlite3.Connection, trial_id: int, updates: dict) -> None:
    unknown = set(updates) - set(TRIAL_UPDATABLE)
    if unknown:
        raise ValueError(f"not updatable: {sorted(unknown)}")
    columns = [column for column in TRIAL_UPDATABLE if column in updates]
    set_clause = ", ".join(f"{column} = ?" for column in columns)
    conn.execute(
        f"UPDATE trials SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*[updates[column] for column in columns], trial_id),
    )


def delete_trial(conn: sqlite3.Connection, trial_id: int) -> None:
    conn.execute("DELETE FROM trials WHERE id = ?", (trial_id,))


# ---- TDS readings ----------------------------------------------------------


def insert_tds_reading(conn: sqlite3.Connection, trial_id: int, tds_pct: float, sample_temp_c: float | None) -> int:
    cursor = conn.execute(
        "INSERT INTO tds_readings (trial_id, tds_pct, sample_temp_c) VALUES (?, ?, ?)",
        (trial_id, tds_pct, sample_temp_c),
    )
    return cursor.lastrowid


def list_tds_readings(conn: sqlite3.Connection, trial_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM tds_readings WHERE trial_id = ? ORDER BY id", (trial_id,)).fetchall()


def count_tds_readings(conn: sqlite3.Connection, trial_id: int) -> int:
    return conn.execute("SELECT COUNT(*) FROM tds_readings WHERE trial_id = ?", (trial_id,)).fetchone()[0]


def find_tds_reading(conn: sqlite3.Connection, reading_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM tds_readings WHERE id = ?", (reading_id,)).fetchone()


def delete_tds_reading(conn: sqlite3.Connection, reading_id: int) -> None:
    conn.execute("DELETE FROM tds_readings WHERE id = ?", (reading_id,))


# ---- sensory evaluations ---------------------------------------------------


def upsert_sensory(conn: sqlite3.Connection, trial_id: int, values: dict) -> None:
    """Create or replace the single evaluation of a trial (UNIQUE(trial_id))."""
    columns = ", ".join(SENSORY_COLUMNS)
    placeholders = ", ".join("?" for _ in SENSORY_COLUMNS)
    updates = ", ".join(f"{column} = excluded.{column}" for column in SENSORY_COLUMNS)
    conn.execute(
        f"""
        INSERT INTO sensory_evaluations (trial_id, {columns})
        VALUES (?, {placeholders})
        ON CONFLICT (trial_id) DO UPDATE SET {updates}, updated_at = CURRENT_TIMESTAMP
        """,
        (trial_id, *(values[column] for column in SENSORY_COLUMNS)),
    )


def find_sensory(conn: sqlite3.Connection, trial_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sensory_evaluations WHERE trial_id = ?", (trial_id,)).fetchone()


def delete_sensory(conn: sqlite3.Connection, trial_id: int) -> None:
    conn.execute("DELETE FROM sensory_evaluations WHERE trial_id = ?", (trial_id,))
