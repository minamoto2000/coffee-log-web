from contextlib import closing
from fastapi import FastAPI
from database import get_connection
from models import EquipmentSetCreate, EquipmentSetRead


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