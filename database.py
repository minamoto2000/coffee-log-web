import sqlite3
from pathlib import Path

DATABASE_PATH = Path("coffee_log_web.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    # Tables will be added as each MVP model is implemented.
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
