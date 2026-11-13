"""Response schema of GET /experiments/{id}/comparison (01b 7.4)."""
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.common import normalize_stored_datetime
from app.schemas.experiments import ConditionLabel


class MetricValueRead(BaseModel):
    trial_id: int
    trial_no: int
    brewed_at: datetime
    value: float

    @field_validator("brewed_at")
    @classmethod
    def normalize_brewed_at(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)


class MetricRead(BaseModel):
    n: int
    values: list[MetricValueRead]
    mean: float | None
    sd: float | None
    median: float | None
    min: float | None
    max: float | None


class ConditionComparisonRead(BaseModel):
    label: ConditionLabel
    condition_id: int
    name: str
    included_trial_count: int
    metrics: dict[str, MetricRead]


class PooledSdRead(BaseModel):
    value: float | None
    groups_used: int
    degrees_of_freedom: int


class SpreadRead(BaseModel):
    value: float | None
    n: int


class TdsVariabilityRead(BaseModel):
    measurement_sd: PooledSdRead  # repeated readings of the same beverage
    between_trial_sd: SpreadRead  # spread of per-trial TDS means


class WarningRead(BaseModel):
    code: str
    count: int | None = None


class DifferenceRead(BaseModel):
    mean_b_minus_a: float | None  # null when either condition has no value


class ComparisonRead(BaseModel):
    experiment_id: int
    include_deviated: bool
    conditions: list[ConditionComparisonRead]
    tds_variability: dict[ConditionLabel, TdsVariabilityRead]
    differences: dict[str, DifferenceRead]
    warnings: list[WarningRead]
