import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# COFFEE_LOG_DB_PATH lets the E2E run (and anyone) point the app at another file.
DB_PATH = Path(os.environ.get("COFFEE_LOG_DB_PATH", Path(__file__).resolve().parent.parent / "coffee_log_web.db"))

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Explicit write transaction.

    BEGIN IMMEDIATE takes the write lock up front, so a check ("does this
    condition already have trials?") and the update that depends on it run
    in the same transaction. Commits on success, rolls back on any error.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filter_label TEXT NOT NULL,
                brewer_label TEXT NOT NULL,
                grinder_label TEXT NOT NULL,
                grind_setting_unit TEXT NOT NULL,
                note TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for statement in EXPERIMENT_SCHEMA:
            conn.execute(statement)
    conn.close()


# Redesigned domain (01b section 6). Derived values (EY, statistics,
# status) are never stored. Type-specific step fields are enforced here as
# well as in the request schema so that invalid rows cannot exist at all.
# A CHECK passes when its expression is NULL, so every comparison on a
# nullable column is guarded by an explicit IS NOT NULL.
EXPERIMENT_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL CHECK (length(trim(title)) > 0),
        hypothesis TEXT NOT NULL CHECK (length(trim(hypothesis)) > 0),
        changed_variable TEXT NOT NULL CHECK (length(trim(changed_variable)) > 0),
        bean_label TEXT NOT NULL CHECK (length(trim(bean_label)) > 0),
        roast_date DATE,
        equipment_set_id INTEGER NOT NULL REFERENCES equipment_sets(id),
        equipment_set_name_snapshot TEXT NOT NULL,
        brewer_label_snapshot TEXT NOT NULL,
        filter_label_snapshot TEXT NOT NULL,
        grinder_label_snapshot TEXT NOT NULL,
        grind_setting_unit_snapshot TEXT NOT NULL,
        extraction_style TEXT NOT NULL
            CHECK (extraction_style IN ('percolation', 'immersion', 'hybrid', 'unknown')),
        ey_method TEXT NOT NULL DEFAULT 'BEVERAGE_MASS_V1'
            CHECK (ey_method IN ('BEVERAGE_MASS_V1')),
        water_label TEXT,
        tds_device_label TEXT,
        fixed_conditions_note TEXT,
        planned_trials_per_condition INTEGER NOT NULL
            CHECK (planned_trials_per_condition BETWEEN 1 AND 20),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
        label TEXT NOT NULL CHECK (label IN ('A', 'B')),
        name TEXT NOT NULL CHECK (length(trim(name)) > 0),
        dose_g REAL NOT NULL CHECK (dose_g > 0),
        grind_setting_value REAL CHECK (grind_setting_value IS NULL OR grind_setting_value >= 0),
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (experiment_id, label)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS protocol_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition_id INTEGER NOT NULL REFERENCES conditions(id) ON DELETE CASCADE,
        seq INTEGER NOT NULL CHECK (seq >= 1),
        step_type TEXT NOT NULL CHECK (step_type IN ('pour', 'agitate', 'other')),
        start_s INTEGER NOT NULL CHECK (start_s >= 0),
        duration_s INTEGER CHECK (duration_s IS NULL OR duration_s >= 0),
        water_g REAL,
        kettle_temp_c REAL,
        agitation_method TEXT,
        label TEXT,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (condition_id, seq),
        CHECK (
            (step_type = 'pour'
                AND water_g IS NOT NULL AND water_g > 0
                AND kettle_temp_c IS NOT NULL AND kettle_temp_c > 0 AND kettle_temp_c <= 100
                AND agitation_method IS NULL AND label IS NULL)
            OR (step_type = 'agitate'
                AND agitation_method IS NOT NULL AND agitation_method IN ('stir', 'swirl', 'other')
                AND water_g IS NULL AND kettle_temp_c IS NULL AND label IS NULL)
            OR (step_type = 'other'
                AND label IS NOT NULL AND length(trim(label)) > 0
                AND water_g IS NULL AND kettle_temp_c IS NULL AND agitation_method IS NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition_id INTEGER NOT NULL REFERENCES conditions(id) ON DELETE RESTRICT,
        trial_no INTEGER NOT NULL CHECK (trial_no >= 1),
        brewed_at TIMESTAMP NOT NULL,
        dose_g_actual REAL NOT NULL CHECK (dose_g_actual > 0),
        beverage_mass_g REAL CHECK (beverage_mass_g IS NULL OR beverage_mass_g > 0),
        brew_time_s INTEGER CHECK (brew_time_s IS NULL OR brew_time_s >= 0),
        followed_plan INTEGER NOT NULL CHECK (followed_plan IN (0, 1)),
        deviation_note TEXT,
        excluded INTEGER NOT NULL DEFAULT 0 CHECK (excluded IN (0, 1)),
        exclusion_reason TEXT,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (condition_id, trial_no),
        CHECK (followed_plan = 1 OR (deviation_note IS NOT NULL AND length(trim(deviation_note)) > 0)),
        CHECK (excluded = 0 OR (exclusion_reason IS NOT NULL AND length(trim(exclusion_reason)) > 0))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tds_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trial_id INTEGER NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
        tds_pct REAL NOT NULL CHECK (tds_pct > 0 AND tds_pct <= 30),
        sample_temp_c REAL CHECK (sample_temp_c IS NULL OR (sample_temp_c > 0 AND sample_temp_c <= 100)),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tds_readings_trial_id ON tds_readings (trial_id)",
    """
    CREATE TABLE IF NOT EXISTS sensory_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trial_id INTEGER NOT NULL UNIQUE REFERENCES trials(id) ON DELETE CASCADE,
        overall_score INTEGER CHECK (overall_score IS NULL OR overall_score BETWEEN 1 AND 10),
        acidity INTEGER CHECK (acidity IS NULL OR acidity BETWEEN 0 AND 5),
        sweetness INTEGER CHECK (sweetness IS NULL OR sweetness BETWEEN 0 AND 5),
        bitterness INTEGER CHECK (bitterness IS NULL OR bitterness BETWEEN 0 AND 5),
        body INTEGER CHECK (body IS NULL OR body BETWEEN 0 AND 5),
        aroma INTEGER CHECK (aroma IS NULL OR aroma BETWEEN 0 AND 5),
        blinded INTEGER NOT NULL CHECK (blinded IN (0, 1)),
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CHECK (
            overall_score IS NOT NULL OR acidity IS NOT NULL OR sweetness IS NOT NULL
            OR bitterness IS NOT NULL OR body IS NOT NULL OR aroma IS NOT NULL
        )
    )
    """,
)
