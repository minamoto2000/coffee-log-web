import json

from contextlib import closing
from fastapi import FastAPI, HTTPException
from database import get_connection
from models import (
    BrewLogCreateRequest,
    BrewLogRead,
    EquipmentSetCreate,
    EquipmentSetRead,
    EquipmentSetUpdate,
    EvaluationRead,
    RecommendationRead,
)

from recommendation import build_recommendation


app = FastAPI(title="Coffee Log Web")

def row_to_brew_log_read(row) -> BrewLogRead:
    brew_log_data = dict(row)
    brew_log_data["pours"] = json.loads(brew_log_data["pours"])
    return BrewLogRead(**brew_log_data)

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

@app.post("/logs")
def create_brew_log(request: BrewLogCreateRequest) -> BrewLogRead:
    brew_log = request.brew_log
    evaluation = request.evaluation

    with closing(get_connection()) as conn:
        equipment_set_row = conn.execute(
            "SELECT * FROM equipment_sets WHERE id = ? AND is_active = 1",
            (brew_log.equipment_set_id,)
        ).fetchone()

        if equipment_set_row is None:
            raise HTTPException(
                status_code=404,
                detail="Equipment set not found"
            )

        pours_json = json.dumps([pour.model_dump() for pour in brew_log.pours])

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO brew_logs (
                    brewed_at,
                    equipment_set_id,
                    bean_label,
                    dose_g,
                    water_g,
                    water_temp_c,
                    grind_setting_value,
                    bloom_time_s,
                    agitation_level,
                    pours,
                    finish_pouring_s,
                    brew_end_s,
                    equipment_set_name_snapshot,
                    brewer_label_snapshot,
                    filter_label_snapshot,
                    grinder_label_snapshot,
                    grind_setting_unit_snapshot,
                    note
                )
                VALUES (
                    COALESCE(?, CURRENT_TIMESTAMP),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """,
                (
                    brew_log.brewed_at,
                    brew_log.equipment_set_id,
                    brew_log.bean_label,
                    brew_log.dose_g,
                    brew_log.water_g,
                    brew_log.water_temp_c,
                    brew_log.grind_setting_value,
                    brew_log.bloom_time_s,
                    brew_log.agitation_level,
                    pours_json,
                    brew_log.finish_pouring_s,
                    brew_log.brew_end_s,
                    equipment_set_row["name"],
                    equipment_set_row["brewer_label"],
                    equipment_set_row["filter_label"],
                    equipment_set_row["grinder_label"],
                    equipment_set_row["grind_setting_unit"],
                    brew_log.note
                )
            )
            brew_log_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO evaluations (
                    brew_log_id,
                    confidence,
                    overall_score,
                    taste_defect,
                    aroma_defect,
                    aftertaste_defect,
                    texture_defect,
                    memo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brew_log_id,
                    evaluation.confidence,
                    evaluation.overall_score,
                    evaluation.taste_defect,
                    evaluation.aroma_defect,
                    evaluation.aftertaste_defect,
                    evaluation.texture_defect,
                    evaluation.memo
                )
            )

            brew_log_row = conn.execute(
                "SELECT * FROM brew_logs WHERE id = ?",
                (brew_log_id,)
            ).fetchone()
            return row_to_brew_log_read(brew_log_row)

@app.get("/logs")
def read_brew_logs() -> list[BrewLogRead]:
    with closing(get_connection()) as conn:
        brew_log_rows = conn.execute("SELECT * FROM brew_logs").fetchall()
        return [row_to_brew_log_read(row) for row in brew_log_rows]

@app.get("/logs/{brew_log_id}")
def read_brew_log(brew_log_id: int) -> BrewLogRead:
    with closing(get_connection()) as conn:
        brew_log_row = conn.execute("SELECT * FROM brew_logs WHERE id = ?", (brew_log_id,)).fetchone()
        if brew_log_row is None:
            raise HTTPException(status_code=404, detail="Brew log not found")

        return row_to_brew_log_read(brew_log_row)

@app.get("/logs/{brew_log_id}/recommendation")
def read_recommendation(brew_log_id: int) -> RecommendationRead:
    with closing(get_connection()) as conn:
        brew_log_row = conn.execute("SELECT * FROM brew_logs WHERE id = ?", (brew_log_id,)).fetchone()
        if brew_log_row is None:
            raise HTTPException(status_code=404, detail="Brew log not found")

        evaluation_row = conn.execute("SELECT * FROM evaluations WHERE brew_log_id = ?", (brew_log_id,)).fetchone()
        if evaluation_row is None:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        brew_log = row_to_brew_log_read(brew_log_row)
        evaluation = EvaluationRead(**dict(evaluation_row))

        recommendation = build_recommendation(brew_log, evaluation)
        return recommendation