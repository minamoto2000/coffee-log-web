from fastapi import APIRouter, Response

from app.schemas.trials import SensoryIn, SensoryRead, TdsReadingIn, TdsReadingRead, TrialCreate, TrialRead, TrialUpdate
from app.services import trials as service

router = APIRouter(tags=["trials"])


@router.post("/conditions/{condition_id}/trials", status_code=201)
def create_trial(condition_id: int, data: TrialCreate) -> TrialRead:
    return service.create(condition_id, data)


@router.get("/trials/{trial_id}")
def get_trial(trial_id: int) -> TrialRead:
    return service.get(trial_id)


@router.patch("/trials/{trial_id}")
def update_trial(trial_id: int, data: TrialUpdate) -> TrialRead:
    return service.update(trial_id, data)


@router.delete("/trials/{trial_id}", status_code=204)
def delete_trial(trial_id: int) -> Response:
    service.delete(trial_id)
    return Response(status_code=204)


@router.post("/trials/{trial_id}/tds-readings", status_code=201)
def add_tds_reading(trial_id: int, data: TdsReadingIn) -> TdsReadingRead:
    return service.add_tds_reading(trial_id, data)


@router.delete("/tds-readings/{reading_id}", status_code=204)
def delete_tds_reading(reading_id: int) -> Response:
    service.delete_tds_reading(reading_id)
    return Response(status_code=204)


@router.put("/trials/{trial_id}/sensory")
def put_sensory(trial_id: int, data: SensoryIn) -> SensoryRead:
    return service.put_sensory(trial_id, data)


@router.delete("/trials/{trial_id}/sensory", status_code=204)
def delete_sensory(trial_id: int) -> Response:
    service.delete_sensory(trial_id)
    return Response(status_code=204)
