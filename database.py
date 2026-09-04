import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "coffee_log_web.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brew_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brewed_at TIMESTAMP NOT NULL,
                equipment_set_id INTEGER NOT NULL,
                bean_label TEXT NOT NULL,
                dose_g REAL NOT NULL,
                water_g REAL NOT NULL,
                water_temp_c REAL NOT NULL,
                grind_setting_value REAL,
                bloom_time_s INTEGER NOT NULL,
                agitation_level INTEGER NOT NULL CHECK(agitation_level BETWEEN 0 AND 3),
                pours TEXT NOT NULL,
                finish_pouring_s INTEGER NOT NULL,
                brew_end_s INTEGER NOT NULL,
                equipment_set_name_snapshot TEXT NOT NULL,
                brewer_label_snapshot TEXT NOT NULL,
                filter_label_snapshot TEXT NOT NULL,
                grinder_label_snapshot TEXT NOT NULL,
                grind_setting_unit_snapshot TEXT NOT NULL,
                note TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_set_id) REFERENCES equipment_sets(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brew_log_id INTEGER NOT NULL UNIQUE,
                confidence INTEGER NOT NULL CHECK(confidence BETWEEN 1 AND 3),
                overall_score INTEGER CHECK(overall_score BETWEEN 1 AND 10),
                taste_defect TEXT NOT NULL CHECK(taste_defect IN ('none', 'thin', 'sour', 'bitter', 'not_sweet')),
                aroma_defect INTEGER NOT NULL CHECK(aroma_defect IN (0, 1)),
                aftertaste_defect INTEGER NOT NULL CHECK(aftertaste_defect IN (0, 1)),
                texture_defect INTEGER NOT NULL CHECK(texture_defect IN (0, 1)),
                memo TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brew_log_id) REFERENCES brew_logs(id) ON DELETE CASCADE,
                CHECK (confidence = 1 OR overall_score IS NOT NULL)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS external_benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consumed_at DATE NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ( 'cafe','convenience_store', 'other')),
                product_name TEXT NOT NULL,
                overall_score INTEGER NOT NULL CHECK(overall_score BETWEEN 1 AND 10),
                note TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    conn.close()
