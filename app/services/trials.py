"""Business rules for trials, TDS readings and sensory evaluations (01b 7, 8.3, 8.4, 8.6)."""
import sqlite3
from contextlib import closing
from datetime import date, datetime

from pydantic import ValidationError

from app.config import APP_TIMEZONE
from app.db import get_connection, transaction
from app.domain.protocol import Step, planned_total_water_g
from app.domain.trial import days_since_roast, trial_measures
from app.errors import ConflictError, EmptyUpdateError, InvalidResourceError, NotFoundError
from app.repositories import experiments as experiment_repository
from app.repositories import trials as repository
from app.schemas.trials import (
    MAX_TDS_READINGS,
    EyRead,
    SensoryIn,
    SensoryRead,
    TdsReadingIn,
    TdsReadingRead,
    TrialCreate,
    TrialDerived,
    TrialFields,
    TrialMeasured,
    TrialRead,
    TrialUpdate,
    ValueWithN,
)

TRIAL_NOT_FOUND = "Trial not found"
CONDITION_NOT_FOUND = "Condition not found"
TDS_READING_NOT_FOUND = "TDS reading not found"
SENSORY_NOT_FOUND = "Sensory evaluation not found"


# ---- trials ----------------------------------------------------------------


def create(condition_id: int, data: TrialCreate) -> TrialRead:
    """Trial + its TDS readings + optional sensory evaluation in one transaction."""
    with closing(get_connection()) as conn:
        with transaction(conn):
            if experiment_repository.find_condition(conn, condition_id) is None:
                raise NotFoundError(CONDITION_NOT_FOUND)
            trial_no = repository.next_trial_no(conn, condition_id)
            trial_id = repository.insert_trial(conn, condition_id, trial_no, _trial_row(data))
            for reading in data.tds_readings:
                _insert_reading(conn, trial_id, reading)
            if data.sensory is not None:
                repository.upsert_sensory(conn, trial_id, _sensory_row(data.sensory))
        return _read(conn, trial_id)


def get(trial_id: int) -> TrialRead:
    with closing(get_connection()) as conn:
        _require_trial(conn, trial_id)
        return _read(conn, trial_id)


def update(trial_id: int, data: TrialUpdate) -> TrialRead:
    """Merge the patch into the stored trial and validate the whole result,
    so that e.g. followed_plan=false cannot be saved without a deviation note.
    """
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise EmptyUpdateError("No fields to update")

    with closing(get_connection()) as conn:
        with transaction(conn):
            current = _require_trial(conn, trial_id)
            merged = {name: current[name] for name in TrialFields.model_fields}
            merged["brewed_at"] = datetime.fromisoformat(current["brewed_at"])
            merged.update(updates)
            try:
                validated = TrialFields(**merged)
            except ValidationError as exc:
                raise InvalidResourceError(_errors(exc)) from None
            repository.update_trial(conn, trial_id, _trial_row(validated))
        return _read(conn, trial_id)


def delete(trial_id: int) -> None:
    """Physical delete for a mistaken entry. To keep a trial but leave it out
    of comparisons, PATCH excluded=true instead."""
    with closing(get_connection()) as conn:
        with transaction(conn):
            _require_trial(conn, trial_id)
            repository.delete_trial(conn, trial_id)


# ---- TDS readings ----------------------------------------------------------


def add_tds_reading(trial_id: int, data: TdsReadingIn) -> TdsReadingRead:
    with closing(get_connection()) as conn:
        with transaction(conn):
            _require_trial(conn, trial_id)
            if repository.count_tds_readings(conn, trial_id) >= MAX_TDS_READINGS:
                raise ConflictError(f"A trial can have at most {MAX_TDS_READINGS} TDS readings")
            reading_id = _insert_reading(conn, trial_id, data)
        return TdsReadingRead(**dict(repository.find_tds_reading(conn, reading_id)))


def delete_tds_reading(reading_id: int) -> None:
    with closing(get_connection()) as conn:
        with transaction(conn):
            if repository.find_tds_reading(conn, reading_id) is None:
                raise NotFoundError(TDS_READING_NOT_FOUND)
            repository.delete_tds_reading(conn, reading_id)


# ---- sensory evaluation ----------------------------------------------------


def put_sensory(trial_id: int, data: SensoryIn) -> SensoryRead:
    with closing(get_connection()) as conn:
        with transaction(conn):
            _require_trial(conn, trial_id)
            repository.upsert_sensory(conn, trial_id, _sensory_row(data))
        return SensoryRead(**dict(repository.find_sensory(conn, trial_id)))


def delete_sensory(trial_id: int) -> None:
    with closing(get_connection()) as conn:
        with transaction(conn):
            _require_trial(conn, trial_id)
            if repository.find_sensory(conn, trial_id) is None:
                raise NotFoundError(SENSORY_NOT_FOUND)
            repository.delete_sensory(conn, trial_id)


# ---- read model ------------------------------------------------------------


def _read(conn: sqlite3.Connection, trial_id: int) -> TrialRead:
    row = repository.find_trial(conn, trial_id)
    readings = [TdsReadingRead(**dict(reading)) for reading in repository.list_tds_readings(conn, trial_id)]
    sensory_row = repository.find_sensory(conn, trial_id)
    steps = experiment_repository.list_steps(conn, row["condition_id"])

    measures = trial_measures([reading.tds_pct for reading in readings], row["beverage_mass_g"], row["dose_g_actual"])
    brewed_at = datetime.fromisoformat(row["brewed_at"])
    roast_date = date.fromisoformat(row["roast_date"]) if row["roast_date"] else None

    return TrialRead(
        id=row["id"],
        experiment_id=row["experiment_id"],
        condition_id=row["condition_id"],
        condition_label=row["condition_label"],
        trial_no=row["trial_no"],
        brewed_at=brewed_at,
        followed_plan=bool(row["followed_plan"]),
        deviation_note=row["deviation_note"],
        excluded=bool(row["excluded"]),
        exclusion_reason=row["exclusion_reason"],
        note=row["note"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        measured=TrialMeasured(
            dose_g_actual=row["dose_g_actual"],
            beverage_mass_g=row["beverage_mass_g"],
            brew_time_s=row["brew_time_s"],
            tds_readings=readings,
        ),
        sensory=SensoryRead(**dict(sensory_row)) if sensory_row else None,
        derived=TrialDerived(
            tds_mean_pct=ValueWithN(value=measures.tds.mean, n=measures.tds.n),
            tds_reading_sd_pct=ValueWithN(value=measures.tds.sd, n=measures.tds.n),
            ey_pct=EyRead(
                value=measures.ey.value,
                method=measures.ey.method,
                inputs=measures.ey.inputs,
                assumptions=measures.ey.assumptions,
                null_reason=measures.ey.null_reason,
            ),
            days_since_roast=days_since_roast(roast_date, brewed_at, APP_TIMEZONE),
            planned_total_water_g=planned_total_water_g(
                [Step(step["step_type"], step["start_s"], water_g=step["water_g"]) for step in steps]
            ),
        ),
    )


# ---- helpers ---------------------------------------------------------------


def _require_trial(conn: sqlite3.Connection, trial_id: int) -> sqlite3.Row:
    row = repository.find_trial(conn, trial_id)
    if row is None:
        raise NotFoundError(TRIAL_NOT_FOUND)
    return row


def _trial_row(data: TrialFields) -> dict:
    return {
        "brewed_at": data.brewed_at.isoformat(),
        "dose_g_actual": float(data.dose_g_actual),
        "beverage_mass_g": _as_float(data.beverage_mass_g),
        "brew_time_s": data.brew_time_s,
        "followed_plan": int(data.followed_plan),
        "deviation_note": data.deviation_note,
        "excluded": int(data.excluded),
        "exclusion_reason": data.exclusion_reason,
        "note": data.note,
    }


def _sensory_row(data: SensoryIn) -> dict:
    values = data.model_dump()
    values["blinded"] = int(data.blinded)
    return values


def _insert_reading(conn: sqlite3.Connection, trial_id: int, reading: TdsReadingIn) -> int:
    return repository.insert_tds_reading(conn, trial_id, float(reading.tds_pct), _as_float(reading.sample_temp_c))


def _errors(exc: ValidationError) -> list[dict]:
    """JSON-safe subset of Pydantic errors (the raw input may hold Decimals)."""
    return [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors(include_url=False)
    ]


def _as_float(value):
    return None if value is None else float(value)
