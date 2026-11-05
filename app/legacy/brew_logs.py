"""Legacy BrewLog / Evaluation API and pages. Removed in the last migration step (PR9)."""
import json
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.db import get_connection
from app.legacy.schemas import (
    BrewLogCreate,
    BrewLogCreateRequest,
    BrewLogCreateResponse,
    BrewLogRead,
    BrewLogUpdateRequest,
    EvaluationRead,
    EvaluationUpdateRequest,
)
from app.services import equipment_sets as equipment_set_service
from app.templating import templates

router = APIRouter(tags=["legacy-brew-logs"])


def row_to_brew_log_read(row) -> BrewLogRead:
    brew_log_data = dict(row)
    brew_log_data["pours"] = json.loads(brew_log_data["pours"])
    return BrewLogRead(**brew_log_data)

@router.post("/logs")
def create_brew_log(request: BrewLogCreateRequest) -> BrewLogCreateResponse:
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
                    ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """,
                (
                    brew_log.brewed_at.isoformat(),
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

            evaluation_row = conn.execute(
                "SELECT * FROM evaluations WHERE brew_log_id = ?",
                (brew_log_id,)
            ).fetchone()

            return BrewLogCreateResponse(
                brew_log=row_to_brew_log_read(brew_log_row),
                evaluation=EvaluationRead(**dict(evaluation_row))
            )

@router.get("/logs")
def read_brew_logs() -> list[BrewLogRead]:
    with closing(get_connection()) as conn:
        brew_log_rows = conn.execute(
            "SELECT * FROM brew_logs ORDER BY brewed_at DESC, id DESC"
        ).fetchall()
        return [row_to_brew_log_read(row) for row in brew_log_rows]

@router.get("/logs/{brew_log_id}")
def read_brew_log(brew_log_id: int) -> BrewLogRead:
    with closing(get_connection()) as conn:
        brew_log_row = conn.execute("SELECT * FROM brew_logs WHERE id = ?", (brew_log_id,)).fetchone()
        if brew_log_row is None:
            raise HTTPException(status_code=404, detail="Brew log not found")

        return row_to_brew_log_read(brew_log_row)

@router.get("/logs/{brew_log_id}/evaluation")
def read_evaluation(brew_log_id: int) -> EvaluationRead:
    with closing(get_connection()) as conn:
        evaluation_row = conn.execute(
            "SELECT * FROM evaluations WHERE brew_log_id = ?",
            (brew_log_id,),
        ).fetchone()

        if evaluation_row is None:
            raise HTTPException(
                status_code=404,
                detail="Evaluation not found",
            )

        return EvaluationRead(**dict(evaluation_row))

@router.patch("/logs/{brew_log_id}/evaluation")
def update_evaluation(
    brew_log_id: int,
    request: EvaluationUpdateRequest,
) -> EvaluationRead:

    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    with closing(get_connection()) as conn:
        evaluation_row = conn.execute(
            "SELECT * FROM evaluations WHERE brew_log_id = ?",
            (brew_log_id,),
        ).fetchone()

        if evaluation_row is None:
            raise HTTPException(
                status_code=404,
                detail="Evaluation not found",
            )

        existing_evaluation = EvaluationRead(**dict(evaluation_row))

        merged_data = existing_evaluation.model_dump()
        merged_data.update(update_data)

        try:
            validated_evaluation = EvaluationRead(**merged_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            )

        with conn:
            conn.execute(
                """
                UPDATE evaluations
                SET confidence = ?,
                    overall_score = ?,
                    taste_defect = ?,
                    aroma_defect = ?,
                    aftertaste_defect = ?,
                    texture_defect = ?,
                    memo = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE brew_log_id = ?
                """,
                (
                    validated_evaluation.confidence,
                    validated_evaluation.overall_score,
                    validated_evaluation.taste_defect,
                    validated_evaluation.aroma_defect,
                    validated_evaluation.aftertaste_defect,
                    validated_evaluation.texture_defect,
                    validated_evaluation.memo,
                    brew_log_id,
                ),
            )

        updated_row = conn.execute(
            "SELECT * FROM evaluations WHERE brew_log_id = ?",
            (brew_log_id,),
        ).fetchone()

        return EvaluationRead(**dict(updated_row))

@router.patch("/logs/{brew_log_id}")
def update_brew_log(
    brew_log_id: int,
    request: BrewLogUpdateRequest,
) -> BrewLogRead:
    
    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    with closing(get_connection()) as conn:
        brew_log_row = conn.execute(
            "SELECT * FROM brew_logs WHERE id = ?",
            (brew_log_id,),
        ).fetchone()

        if brew_log_row is None:
            raise HTTPException(
                status_code=404,
                detail="Brew log not found",
            )

        existing_brew_log = row_to_brew_log_read(brew_log_row)

        merged_data = {
            "brewed_at": existing_brew_log.brewed_at,
            "equipment_set_id": existing_brew_log.equipment_set_id,
            "bean_label": existing_brew_log.bean_label,
            "dose_g": existing_brew_log.dose_g,
            "water_g": existing_brew_log.water_g,
            "water_temp_c": existing_brew_log.water_temp_c,
            "grind_setting_value": existing_brew_log.grind_setting_value,
            "bloom_time_s": existing_brew_log.bloom_time_s,
            "agitation_level": existing_brew_log.agitation_level,
            "pours": existing_brew_log.pours,
            "finish_pouring_s": existing_brew_log.finish_pouring_s,
            "brew_end_s": existing_brew_log.brew_end_s,
            "note": existing_brew_log.note,
        }

        merged_data.update(update_data)

        try:
            validated_brew_log = BrewLogCreate(**merged_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            )

        pours_json = json.dumps(
            [pour.model_dump() for pour in validated_brew_log.pours]
        )

        with conn:
            conn.execute(
                """
                UPDATE brew_logs
                SET brewed_at = ?,
                    bean_label = ?,
                    dose_g = ?,
                    water_g = ?,
                    water_temp_c = ?,
                    grind_setting_value = ?,
                    bloom_time_s = ?,
                    agitation_level = ?,
                    pours = ?,
                    finish_pouring_s = ?,
                    brew_end_s = ?,
                    note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    validated_brew_log.brewed_at.isoformat(),
                    validated_brew_log.bean_label,
                    validated_brew_log.dose_g,
                    validated_brew_log.water_g,
                    validated_brew_log.water_temp_c,
                    validated_brew_log.grind_setting_value,
                    validated_brew_log.bloom_time_s,
                    validated_brew_log.agitation_level,
                    pours_json,
                    validated_brew_log.finish_pouring_s,
                    validated_brew_log.brew_end_s,
                    validated_brew_log.note,
                    brew_log_id,
                ),
            )

        updated_row = conn.execute(
            "SELECT * FROM brew_logs WHERE id = ?",
            (brew_log_id,),
        ).fetchone()

        return row_to_brew_log_read(updated_row)

@router.delete("/logs/{brew_log_id}")
def delete_brew_log(brew_log_id: int) -> BrewLogRead:
    with closing(get_connection()) as conn:
        brew_log_row = conn.execute("SELECT * FROM brew_logs WHERE id = ?", (brew_log_id,)).fetchone()

        if brew_log_row is None:
            raise HTTPException(status_code=404, detail="Brew log not found")

        deleted_brew_log = row_to_brew_log_read(brew_log_row)

        with conn:
            conn.execute("DELETE FROM brew_logs WHERE id = ?", (brew_log_id,))

        return deleted_brew_log

@router.get("/pages/logs")
def brew_logs_page(request: Request):
    brew_logs = read_brew_logs()
    return templates.TemplateResponse(
        request=request,
        name="brew_logs.html",
        context={"brew_logs": brew_logs},
    )


@router.get("/pages/logs/new")
def new_brew_log_page(request: Request):
    equipment_sets = equipment_set_service.list_active()
    return templates.TemplateResponse(
        request=request,
        name="brew_log_form.html",
        context={"equipment_sets": equipment_sets},
    )


@router.get("/pages/logs/{brew_log_id}")
def brew_log_detail_page(request: Request, brew_log_id: int):
    brew_log = read_brew_log(brew_log_id)
    evaluation = read_evaluation(brew_log_id)
    return templates.TemplateResponse(
        request=request,
        name="brew_log_detail.html",
        context={
            "brew_log": brew_log,
            "evaluation": evaluation,
        },
    )
