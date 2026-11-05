import sqlite3

# Columns that PATCH may change. The SET clause is built only from this list.
UPDATABLE_COLUMNS = (
    "name",
    "filter_label",
    "brewer_label",
    "grinder_label",
    "grind_setting_unit",
    "note",
)


def insert(conn: sqlite3.Connection, values: dict) -> int:
    cursor = conn.execute(
        """
        INSERT INTO equipment_sets (
            name, filter_label, brewer_label, grinder_label, grind_setting_unit, note
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            values["name"],
            values["filter_label"],
            values["brewer_label"],
            values["grinder_label"],
            values["grind_setting_unit"],
            values["note"],
        ),
    )
    return cursor.lastrowid


def find_by_id(conn: sqlite3.Connection, equipment_set_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM equipment_sets WHERE id = ?",
        (equipment_set_id,),
    ).fetchone()


def find_active_by_id(conn: sqlite3.Connection, equipment_set_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1",
        (equipment_set_id,),
    ).fetchone()


def list_active(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM equipment_sets WHERE is_active = 1").fetchall()


def update_fields(conn: sqlite3.Connection, equipment_set_id: int, updates: dict) -> None:
    unknown = set(updates) - set(UPDATABLE_COLUMNS)
    if unknown:
        raise ValueError(f"not updatable: {sorted(unknown)}")

    columns = [column for column in UPDATABLE_COLUMNS if column in updates]
    set_clause = ", ".join(f"{column} = ?" for column in columns)
    values = [updates[column] for column in columns]
    conn.execute(
        f"UPDATE equipment_sets SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*values, equipment_set_id),
    )


def deactivate(conn: sqlite3.Connection, equipment_set_id: int) -> None:
    conn.execute(
        "UPDATE equipment_sets SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (equipment_set_id,),
    )
