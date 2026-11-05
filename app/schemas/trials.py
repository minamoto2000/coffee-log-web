"""Request / response schemas for trials, TDS readings and sensory evaluations (01b 6.4-6.6, 7.3, 8.3)."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import TimestampsRead, normalize_stored_datetime, require_offset_utc
from app.schemas.experiments import ConditionLabel, Mass, Temperature

MAX_TDS_READINGS = 10

TdsPercent = Annotated[Decimal, Field(gt=0, le=30, decimal_places=2)]
Intensity = Annotated[int, Field(ge=0, le=5)]
OverallScore = Annotated[int, Field(ge=1, le=10)]


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class TdsReadingIn(BaseModel):
    tds_pct: TdsPercent
    sample_temp_c: Temperature | None = None


SENSORY_RATINGS = ("overall_score", "acidity", "sweetness", "bitterness", "body", "aroma")


class SensoryIn(BaseModel):
    overall_score: OverallScore | None = None
    acidity: Intensity | None = None
    sweetness: Intensity | None = None
    bitterness: Intensity | None = None
    body: Intensity | None = None
    aroma: Intensity | None = None
    blinded: bool
    note: str | None = None

    @model_validator(mode="after")
    def require_one_rating(self):
        if all(getattr(self, name) is None for name in SENSORY_RATINGS):
            raise ValueError("at least one of overall_score or the attribute intensities is required")
        return self


class TrialFields(BaseModel):
    """The trial row itself. Validated on create and again after a PATCH merge."""

    brewed_at: datetime
    dose_g_actual: Mass
    beverage_mass_g: Mass | None = None
    brew_time_s: int | None = Field(default=None, ge=0)
    followed_plan: bool
    deviation_note: str | None = None
    excluded: bool = False
    exclusion_reason: str | None = None
    note: str | None = None

    @field_validator("brewed_at")
    @classmethod
    def brewed_at_needs_offset(cls, value: datetime) -> datetime:
        return require_offset_utc(value)

    @field_validator("deviation_note", "exclusion_reason", mode="before")
    @classmethod
    def strip_reasons(cls, value):
        return _blank_to_none(value)

    @model_validator(mode="after")
    def reasons_are_required(self):
        if not self.followed_plan and self.deviation_note is None:
            raise ValueError("deviation_note is required when followed_plan is false")
        if self.excluded and self.exclusion_reason is None:
            raise ValueError("exclusion_reason is required when excluded is true")
        return self


class TrialCreate(TrialFields):
    tds_readings: list[TdsReadingIn] = Field(default_factory=list, max_length=MAX_TDS_READINGS)
    sensory: SensoryIn | None = None


class TrialUpdate(BaseModel):
    """PATCH: omitted = keep, explicit null = clear (nullable fields only).

    The condition cannot be changed: a trial belongs to the plan it followed.
    """

    brewed_at: datetime | None = None
    dose_g_actual: Mass | None = None
    beverage_mass_g: Mass | None = None
    brew_time_s: int | None = Field(default=None, ge=0)
    followed_plan: bool | None = None
    deviation_note: str | None = None
    excluded: bool | None = None
    exclusion_reason: str | None = None
    note: str | None = None

    @field_validator("brewed_at", "dose_g_actual", "followed_plan", "excluded")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("field cannot be null")
        return value


# ---- responses -------------------------------------------------------------


class TdsReadingRead(TimestampsRead):
    id: int
    trial_id: int
    tds_pct: float
    sample_temp_c: float | None


class SensoryRead(TimestampsRead):
    id: int
    trial_id: int
    overall_score: int | None
    acidity: int | None
    sweetness: int | None
    bitterness: int | None
    body: int | None
    aroma: int | None
    blinded: bool
    note: str | None


class TrialMeasured(BaseModel):
    dose_g_actual: float
    beverage_mass_g: float | None
    brew_time_s: int | None
    tds_readings: list[TdsReadingRead]


class ValueWithN(BaseModel):
    value: float | None
    n: int


class EyRead(BaseModel):
    value: float | None
    method: str
    inputs: dict[str, float | None]
    assumptions: list[str]
    null_reason: str | None


class TrialDerived(BaseModel):
    tds_mean_pct: ValueWithN
    tds_reading_sd_pct: ValueWithN
    ey_pct: EyRead
    days_since_roast: int | None
    planned_total_water_g: float


class TrialRead(TimestampsRead):
    id: int
    experiment_id: int
    condition_id: int
    condition_label: ConditionLabel
    trial_no: int
    brewed_at: datetime
    followed_plan: bool
    deviation_note: str | None
    excluded: bool
    exclusion_reason: str | None
    note: str | None
    measured: TrialMeasured
    sensory: SensoryRead | None
    derived: TrialDerived

    @field_validator("brewed_at")
    @classmethod
    def normalize_brewed_at(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)
