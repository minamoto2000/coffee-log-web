import sqlite3
from pathlib import Path

DB_NAME = Path("coffee_log_web.db").resolve().parent


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

    conn.close()
