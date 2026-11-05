"""Business rules for experiments and conditions (01b 5, 7.2, 8.2, 8.6)."""
import sqlite3
from contextlib import closing
from datetime import datetime

from app.db import get_connection, transaction
from app.domain import experiment as experiment_domain
from app.domain.protocol import ConditionPlan, Step, condition_diff, planned_total_water_g
from app.domain.trial import trial_measures
from app.errors import ConflictError, EmptyUpdateError, NotFoundError
from app.repositories import equipment_sets as equipment_repository
from app.repositories import experiments as repository
from app.schemas.experiments import (
    FIXED_FIELDS,
    ConditionDiffRead,
    ConditionRead,
    ConditionUpdate,
    DiffItemRead,
    ExperimentCreate,
    ExperimentListItem,
    ExperimentRead,
    ExperimentUpdate,
    ProtocolIn,
    StepRead,
    TrialSummary,
)

EXPERIMENT_NOT_FOUND = "Experiment not found"
CONDITION_NOT_FOUND = "Condition not found"
EQUIPMENT_SET_NOT_FOUND = "Equipment set not found"


# ---- commands --------------------------------------------------------------


def create(data: ExperimentCreate) -> ExperimentRead:
    """Experiment + 2 conditions + their steps in one transaction."""
    with closing(get_connection()) as conn:
        with transaction(conn):
            equipment = equipment_repository.find_active_by_id(conn, data.equipment_set_id)
            if equipment is None:
                raise NotFoundError(EQUIPMENT_SET_NOT_FOUND)

            values = {key: _stored(value) for key, value in data.model_dump(exclude={"conditions"}).items()}
            values.update(_equipment_snapshot(equipment))
            experiment_id = repository.insert_experiment(conn, values)

            for condition in data.conditions:
                condition_id = repository.insert_condition(
                    conn,
                    experiment_id,
                    {
                        "label": condition.label,
                        "name": condition.name,
                        "dose_g": float(condition.dose_g),
                        "grind_setting_value": _as_float(condition.grind_setting_value),
                        "note": condition.note,
                    },
                )
                repository.insert_steps(conn, condition_id, _step_rows(condition))
        return _read(conn, experiment_id)


def update(experiment_id: int, data: ExperimentUpdate) -> ExperimentRead:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise EmptyUpdateError("No fields to update")

    with closing(get_connection()) as conn:
        with transaction(conn):
            current = repository.find_experiment(conn, experiment_id)
            if current is None:
                raise NotFoundError(EXPERIMENT_NOT_FOUND)

            changed_fixed = [
                name for name in FIXED_FIELDS if name in updates and _stored(updates[name]) != current[name]
            ]
            if changed_fixed and repository.count_trials_for_experiment(conn, experiment_id) > 0:
                raise ConflictError(
                    "Fixed conditions cannot change after trials exist: " + ", ".join(changed_fixed)
                )

            if "equipment_set_id" in updates and updates["equipment_set_id"] != current["equipment_set_id"]:
                equipment = equipment_repository.find_active_by_id(conn, updates["equipment_set_id"])
                if equipment is None:
                    raise NotFoundError(EQUIPMENT_SET_NOT_FOUND)
                updates.update(_equipment_snapshot(equipment))

            repository.update_experiment(conn, experiment_id, {k: _stored(v) for k, v in updates.items()})
        return _read(conn, experiment_id)


def delete(experiment_id: int) -> None:
    with closing(get_connection()) as conn:
        with transaction(conn):
            if repository.find_experiment(conn, experiment_id) is None:
                raise NotFoundError(EXPERIMENT_NOT_FOUND)
            if repository.count_trials_for_experiment(conn, experiment_id) > 0:
                raise ConflictError("Experiment with trials cannot be deleted")
            repository.delete_experiment(conn, experiment_id)


def update_condition(condition_id: int, data: ConditionUpdate) -> ConditionRead:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise EmptyUpdateError("No fields to update")

    with closing(get_connection()) as conn:
        with transaction(conn):
            if repository.find_condition(conn, condition_id) is None:
                raise NotFoundError(CONDITION_NOT_FOUND)
            repository.update_condition(conn, condition_id, updates)
        return _condition_read(conn, repository.find_condition(conn, condition_id))


def replace_protocol(condition_id: int, data: ProtocolIn) -> ConditionRead:
    """Replace dose, grind setting and all steps. Forbidden once the condition
    has a trial, so that every trial keeps pointing at the plan it followed.
    """
    with closing(get_connection()) as conn:
        with transaction(conn):
            if repository.find_condition(conn, condition_id) is None:
                raise NotFoundError(CONDITION_NOT_FOUND)
            if repository.count_trials_for_condition(conn, condition_id) > 0:
                raise ConflictError("Plan cannot change after trials exist; create a new experiment")
            repository.update_condition(
                conn,
                condition_id,
                {"dose_g": float(data.dose_g), "grind_setting_value": _as_float(data.grind_setting_value)},
            )
            repository.delete_steps(conn, condition_id)
            repository.insert_steps(conn, condition_id, _step_rows(data))
        return _condition_read(conn, repository.find_condition(conn, condition_id))


# ---- queries ---------------------------------------------------------------


def get(experiment_id: int) -> ExperimentRead:
    with closing(get_connection()) as conn:
        if repository.find_experiment(conn, experiment_id) is None:
            raise NotFoundError(EXPERIMENT_NOT_FOUND)
        return _read(conn, experiment_id)


def list_all() -> list[ExperimentListItem]:
    with closing(get_connection()) as conn:
        items = []
        for row in repository.list_experiments(conn):
            trials = repository.list_trials_for_experiment(conn, row["id"])
            refs = [_trial_ref(trial) for trial in trials]
            items.append(
                ExperimentListItem(
                    id=row["id"],
                    title=row["title"],
                    bean_label=row["bean_label"],
                    created_at=row["created_at"],
                    status=experiment_domain.experiment_status(refs, row["planned_trials_per_condition"]),
                    trial_counts={
                        label: sum(1 for trial in trials if trial["condition_label"] == label)
                        for label in experiment_domain.LABELS
                    },
                )
            )
        return items


# ---- assembling the read model ---------------------------------------------


def _read(conn: sqlite3.Connection, experiment_id: int) -> ExperimentRead:
    row = repository.find_experiment(conn, experiment_id)
    conditions = [_condition_read(conn, condition) for condition in repository.list_conditions(conn, experiment_id)]
    by_label = {condition.label: condition for condition in conditions}
    diff = condition_diff(_plan(by_label["A"]), _plan(by_label["B"]))

    trials = repository.list_trials_for_experiment(conn, experiment_id)
    trial_ids = [trial["id"] for trial in trials]
    readings = repository.tds_readings_by_trial(conn, trial_ids)
    scores = repository.overall_scores_by_trial(conn, trial_ids)
    refs = [_trial_ref(trial) for trial in trials]

    return ExperimentRead(
        **dict(row),
        status=experiment_domain.experiment_status(refs, row["planned_trials_per_condition"]),
        conditions=conditions,
        condition_diff=ConditionDiffRead(
            items=[DiffItemRead(path=item.path, a=item.a, b=item.b) for item in diff],
            count=len(diff),
        ),
        trials=[_trial_summary(trial, readings[trial["id"]], scores.get(trial["id"])) for trial in trials],
        next_condition_label=experiment_domain.next_condition_label(refs),
    )


def _condition_read(conn: sqlite3.Connection, row: sqlite3.Row) -> ConditionRead:
    steps = [StepRead(**{key: step[key] for key in StepRead.model_fields}) for step in repository.list_steps(conn, row["id"])]
    return ConditionRead(
        **dict(row),
        planned_total_water_g=planned_total_water_g(
            [Step(step.step_type, step.start_s, water_g=step.water_g) for step in steps]
        ),
        steps=steps,
    )


def _plan(condition: ConditionRead) -> ConditionPlan:
    return ConditionPlan(
        dose_g=condition.dose_g,
        grind_setting_value=condition.grind_setting_value,
        steps=tuple(
            Step(
                step_type=step.step_type,
                start_s=step.start_s,
                duration_s=step.duration_s,
                water_g=step.water_g,
                kettle_temp_c=step.kettle_temp_c,
                agitation_method=step.agitation_method,
                label=step.label,
                note=step.note,
            )
            for step in condition.steps
        ),
    )


def _trial_ref(trial: sqlite3.Row) -> experiment_domain.TrialRef:
    return experiment_domain.TrialRef(
        condition_label=trial["condition_label"],
        trial_id=trial["id"],
        brewed_at=datetime.fromisoformat(trial["brewed_at"]),
        excluded=bool(trial["excluded"]),
    )


def _trial_summary(trial: sqlite3.Row, readings: list[float], overall_score: int | None) -> TrialSummary:
    measures = trial_measures(readings, trial["beverage_mass_g"], trial["dose_g_actual"])
    return TrialSummary(
        id=trial["id"],
        condition_label=trial["condition_label"],
        trial_no=trial["trial_no"],
        brewed_at=trial["brewed_at"],
        followed_plan=bool(trial["followed_plan"]),
        excluded=bool(trial["excluded"]),
        tds_mean_pct=measures.tds.mean,
        ey_pct=measures.ey.value,
        overall_score=overall_score,
    )


# ---- small helpers ---------------------------------------------------------


def _equipment_snapshot(equipment: sqlite3.Row) -> dict:
    return {
        "equipment_set_name_snapshot": equipment["name"],
        "brewer_label_snapshot": equipment["brewer_label"],
        "filter_label_snapshot": equipment["filter_label"],
        "grinder_label_snapshot": equipment["grinder_label"],
        "grind_setting_unit_snapshot": equipment["grind_setting_unit"],
    }


def _step_rows(protocol: ProtocolIn) -> list[dict]:
    return [
        {
            "step_type": step.step_type,
            "start_s": step.start_s,
            "duration_s": step.duration_s,
            "water_g": _as_float(step.water_g),
            "kettle_temp_c": _as_float(step.kettle_temp_c),
            "agitation_method": step.agitation_method,
            "label": step.label,
            "note": step.note,
        }
        for step in protocol.steps
    ]


def _as_float(value):
    return None if value is None else float(value)


def _stored(value):
    """Value as SQLite stores it, so a PATCH can be compared with the row."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
