from fastapi import APIRouter, Response

from app.schemas.experiments import (
    ConditionRead,
    ConditionUpdate,
    ExperimentCreate,
    ExperimentListItem,
    ExperimentRead,
    ExperimentUpdate,
    ProtocolIn,
)
from app.services import experiments as service

router = APIRouter(tags=["experiments"])


@router.post("/experiments", status_code=201)
def create_experiment(data: ExperimentCreate) -> ExperimentRead:
    return service.create(data)


@router.get("/experiments")
def list_experiments() -> list[ExperimentListItem]:
    return service.list_all()


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: int) -> ExperimentRead:
    return service.get(experiment_id)


@router.patch("/experiments/{experiment_id}")
def update_experiment(experiment_id: int, data: ExperimentUpdate) -> ExperimentRead:
    return service.update(experiment_id, data)


@router.delete("/experiments/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: int) -> Response:
    service.delete(experiment_id)
    return Response(status_code=204)


@router.patch("/conditions/{condition_id}")
def update_condition(condition_id: int, data: ConditionUpdate) -> ConditionRead:
    return service.update_condition(condition_id, data)


@router.put("/conditions/{condition_id}/protocol")
def replace_protocol(condition_id: int, data: ProtocolIn) -> ConditionRead:
    return service.replace_protocol(condition_id, data)
