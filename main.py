from contextlib import closing
from fastapi import FastAPI, HTTPException
from database import get_connection
from models import EquipmentSetCreate, EquipmentSetRead, EquipmentSetUpdate


app = FastAPI(title="Coffee Log Web")

@app.post("/equipment-sets")
def create_equipment_set(equipment_set: EquipmentSetCreate) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        with conn:
            cursor = conn.execute(
                    """
                    INSERT INTO equipment_sets (
                        name, 
                        filter_label, 
                        brewer_label, 
                        grinder_label, 
                        grind_setting_unit,
                        note
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        equipment_set.name,
                        equipment_set.filter_label,
                        equipment_set.brewer_label,
                        equipment_set.grinder_label,
                        equipment_set.grind_setting_unit,
                        equipment_set.note
                    ),
                )
            equipment_set_id = cursor.lastrowid

        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ?", 
            (equipment_set_id,)
            ).fetchone()
        return EquipmentSetRead(**dict(row))

@app.get("/equipment-sets")
def read_equipment_sets() -> list[EquipmentSetRead]:
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM equipment_sets WHERE is_active = 1").fetchall()
        return [EquipmentSetRead(**dict(row)) for row in rows]

@app.get("/equipment-sets/{equipment_set_id}")
def read_equipment_set(equipment_set_id: int) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1", 
            (equipment_set_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Equipment set not found")
        return EquipmentSetRead(**dict(row))

@app.patch("/equipment-sets/{equipment_set_id}")
def update_equipment_set(equipment_set_id: int, equipment_set: EquipmentSetUpdate) -> EquipmentSetRead:
    updates = equipment_set.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1",
            (equipment_set_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Equipment set not found")
        
        with conn:
            parts = []
            for field in updates:
                parts.append(f"{field} = ?")

            set_clause = ", ".join(parts)

            values = list(updates.values())
            values.append(equipment_set_id)

            sql = f"""
                UPDATE equipment_sets
                SET {set_clause},
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """

            conn.execute(sql, values)

        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1",
            (equipment_set_id,)
        ).fetchone()

        return EquipmentSetRead(**dict(row))

@app.delete("/equipment-sets/{equipment_set_id}")
def delete_equipment_set(equipment_set_id: int) -> EquipmentSetRead:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1",
            (equipment_set_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Equipment set not found"
            )

        with conn:
            conn.execute(
                """
                UPDATE equipment_sets
                SET is_active = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (equipment_set_id,)
            )

        row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ?",
            (equipment_set_id,)
        ).fetchone()

        return EquipmentSetRead(**dict(row))
