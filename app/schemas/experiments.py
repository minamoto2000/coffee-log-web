"""Request / response schemas for experiments and conditions (01b 7.1, 7.2, 8.1, 8.2)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.protocol import ConditionPlan, Step, validate_steps
from app.schemas.common import normalize_stored_datetime

# Precision rules (01b 8.5): over-precise input is rejected, never rounded.
Mass = Annotated[Decimal, Field(gt=0, decimal_places=2)]
Temperature = Annotated[Decimal, Field(gt=0, le=100, decimal_places=1)]
GrindSetting = Annotated[Decimal, Field(ge=0, decimal_places=2)]

ExtractionStyle = Literal["percolation", "immersion", "hybrid", "unknown"]
ConditionLabel = Literal["A", "B"]
StepType = Literal["pour", "agitate", "other"]
AgitationMethod = Literal["stir", "swirl", "other"]

REQUIRED_TEXT = Field(min_length=1, max_length=200)


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _as_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class StepIn(BaseModel):
    step_type: StepType
    start_s: int = Field(ge=0)
    duration_s: int | None = Field(default=None, ge=0)
    water_g: Mass | None = None
    kettle_temp_c: Temperature | None = None
    agitation_method: AgitationMethod | None = None
    label: str | None = Field(default=None, max_length=100)
    note: str | None = None

    @field_validator("label", mode="before")
    @classmethod
    def strip_label(cls, value):
        value = _strip(value)
        return value or None

    def to_domain(self) -> Step:
        return Step(
            step_type=self.step_type,
            start_s=self.start_s,
            duration_s=self.duration_s,
            water_g=_as_float(self.water_g),
            kettle_temp_c=_as_float(self.kettle_temp_c),
            agitation_method=self.agitation_method,
            label=self.label,
            note=self.note,
        )


def _check_steps(steps: list[StepIn]) -> None:
    errors = validate_steps([step.to_domain() for step in steps])
    if errors:
        raise ValueError("; ".join(errors))


class ProtocolIn(BaseModel):
    """The plan part of a condition: replaced as a whole (PUT .../protocol)."""

    dose_g: Mass
    grind_setting_value: GrindSetting | None = None
    steps: list[StepIn]

    @model_validator(mode="after")
    def check_steps(self):
        _check_steps(self.steps)
        return self

    def to_domain(self) -> ConditionPlan:
        return ConditionPlan(
            dose_g=float(self.dose_g),
            grind_setting_value=_as_float(self.grind_setting_value),
            steps=tuple(step.to_domain() for step in self.steps),
        )


class ConditionIn(ProtocolIn):
    label: ConditionLabel
    name: str = REQUIRED_TEXT
    note: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return _strip(value)


class ExperimentCreate(BaseModel):
    title: str = REQUIRED_TEXT
    hypothesis: str = Field(min_length=1, max_length=2000)
    changed_variable: str = REQUIRED_TEXT
    bean_label: str = REQUIRED_TEXT
    roast_date: date | None = None
    equipment_set_id: int = Field(ge=1)
    extraction_style: ExtractionStyle
    water_label: str | None = Field(default=None, max_length=200)
    tds_device_label: str | None = Field(default=None, max_length=200)
    fixed_conditions_note: str | None = None
    planned_trials_per_condition: int = Field(ge=1, le=20)
    conditions: list[ConditionIn]

    @field_validator("title", "hypothesis", "changed_variable", "bean_label", mode="before")
    @classmethod
    def strip_required(cls, value):
        return _strip(value)

    @model_validator(mode="after")
    def check_conditions(self):
        labels = sorted(condition.label for condition in self.conditions)
        if labels != ["A", "B"]:
            raise ValueError("conditions must contain exactly one A and one B")
        return self


# Fields that become fixed once the experiment has a trial (01b 8.2).
FIXED_FIELDS = (
    "bean_label",
    "roast_date",
    "equipment_set_id",
    "extraction_style",
    "water_label",
    "tds_device_label",
)


class ExperimentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    hypothesis: str | None = Field(default=None, min_length=1, max_length=2000)
    changed_variable: str | None = Field(default=None, min_length=1, max_length=200)
    bean_label: str | None = Field(default=None, min_length=1, max_length=200)
    roast_date: date | None = None
    equipment_set_id: int | None = Field(default=None, ge=1)
    extraction_style: ExtractionStyle | None = None
    water_label: str | None = Field(default=None, max_length=200)
    tds_device_label: str | None = Field(default=None, max_length=200)
    fixed_conditions_note: str | None = None
    planned_trials_per_condition: int | None = Field(default=None, ge=1, le=20)

    @field_validator("title", "hypothesis", "changed_variable", "bean_label", mode="before")
    @classmethod
    def strip_required(cls, value):
        return _strip(value)

    @field_validator(
        "title",
        "hypothesis",
        "changed_variable",
        "bean_label",
        "equipment_set_id",
        "extraction_style",
        "planned_trials_per_condition",
    )
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ConditionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return _strip(value)

    @field_validator("name")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("field cannot be null")
        return value


# ---- responses -------------------------------------------------------------


class _Timestamps(BaseModel):
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)


class StepRead(BaseModel):
    seq: int
    step_type: StepType
    start_s: int
    duration_s: int | None
    water_g: float | None
    kettle_temp_c: float | None
    agitation_method: AgitationMethod | None
    label: str | None
    note: str | None


class ConditionRead(_Timestamps):
    id: int
    experiment_id: int
    label: ConditionLabel
    name: str
    dose_g: float
    grind_setting_value: float | None
    note: str | None
    planned_total_water_g: float
    steps: list[StepRead]


class DiffItemRead(BaseModel):
    path: str
    a: float | int | str | None
    b: float | int | str | None


class ConditionDiffRead(BaseModel):
    items: list[DiffItemRead]
    count: int


class TrialSummary(BaseModel):
    id: int
    condition_label: ConditionLabel
    trial_no: int
    brewed_at: datetime
    followed_plan: bool
    excluded: bool
    tds_mean_pct: float | None
    ey_pct: float | None
    overall_score: int | None

    @field_validator("brewed_at")
    @classmethod
    def normalize_brewed_at(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)


class ExperimentRead(_Timestamps):
    id: int
    title: str
    hypothesis: str
    changed_variable: str
    bean_label: str
    roast_date: date | None
    equipment_set_id: int
    equipment_set_name_snapshot: str
    brewer_label_snapshot: str
    filter_label_snapshot: str
    grinder_label_snapshot: str
    grind_setting_unit_snapshot: str
    extraction_style: ExtractionStyle
    ey_method: str
    water_label: str | None
    tds_device_label: str | None
    fixed_conditions_note: str | None
    planned_trials_per_condition: int
    status: Literal["DRAFT", "RUNNING", "PLANNED_REACHED"]
    conditions: list[ConditionRead]
    condition_diff: ConditionDiffRead
    trials: list[TrialSummary]
    next_condition_label: ConditionLabel


class ExperimentListItem(BaseModel):
    id: int
    title: str
    bean_label: str
    created_at: datetime
    status: Literal["DRAFT", "RUNNING", "PLANNED_REACHED"]
    trial_counts: dict[str, int]

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)
