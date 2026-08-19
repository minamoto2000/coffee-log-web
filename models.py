from pydantic import BaseModel, Field, model_validator
from typing import Literal
from datetime import datetime, date

class EquipmentSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Name of the equipment set")
    filter_label: str = Field(min_length=1, max_length=100, description="Label for the filter")
    brewer_label: str = Field(min_length=1, max_length=100, description="Label for the brewer")
    grinder_label: str = Field(min_length=1, max_length=100, description="Label for the grinder")
    grind_setting_unit: Literal["click", "step", "number", "other"] = Field(description="Unit for the grind setting")
    note: str | None = Field(default=None, description="Optional note about the equipment")

class EquipmentSetRead(EquipmentSetCreate):
    id: int = Field(description="Primary key")
    is_active: bool = Field(description="Whether the equipment set is active")
    created_at: datetime = Field(description="Timestamp when the equipment set was created")
    updated_at: datetime = Field(description="Timestamp when the equipment set was last updated")

class EquipmentSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100, description="Name of the equipment set")
    filter_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the filter")
    brewer_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the brewer")
    grinder_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the grinder")
    grind_setting_unit: Literal["click", "step", "number", "other"] | None = Field(default=None, description="Unit for the grind setting")
    note: str | None = Field(default=None, description="Optional note about the equipment")

class Pour(BaseModel):
    grams: float = Field(gt=0, description="Amount of water poured in grams")
    at_s: int = Field(ge=0, description="Time in seconds when the pour started")

class BrewLogCreate(BaseModel):
    brewed_at: datetime | None = Field(default=None, description="Timestamp when the brew was made")
    equipment_set_id: int = Field(ge=1, description="Reference to equipment_sets.id")
    bean_label: str = Field(min_length=1, max_length=100, description="Bean name, product name, or identifier")
    dose_g: float = Field(description="Dose in grams")
    water_g: float = Field(description="Water amount in grams")
    water_temp_c: float = Field(description="Water temperature in Celsius")
    grind_setting_value: float  | None = Field(default=None, description="Grind setting value")
    bloom_time_s: int = Field(ge=0, description="Bloom time in seconds")
    agitation_level: int = Field(ge=0, le=3, description="Agitation level from 0 to 3")
    pours: list[Pour] = Field(min_length=1, description="List of pours")
    finish_pouring_s: int = Field(ge=0, description="Time when the last pour was completed")
    brew_end_s: int = Field(ge=0, description="Time when brewing was completed")
    note: str | None = Field(default=None, description="Additional notes")

class BrewLogRead(BrewLogCreate):
    id: int = Field(description="Primary key")
    brewed_at: datetime = Field(description="Timestamp when the brew was made")
    equipment_set_name_snapshot: str = Field(min_length=1, max_length=100, description="Name of the equipment set")
    brewer_label_snapshot: str = Field(min_length=1, max_length=100, description="Snapshot of the brewer label at the time of brewing")
    grind_setting_unit_snapshot: Literal["click", "step", "number", "other"] = Field(description="Unit for the grind setting")
    filter_label_snapshot: str = Field(min_length=1, max_length=100, description="Snapshot of the filter label at the time of brewing")
    grinder_label_snapshot: str = Field(min_length=1, max_length=100, description="Snapshot of the grinder label at the time of brewing")
    created_at: datetime = Field(description="Timestamp when the brew log was created")
    updated_at: datetime = Field(description="Timestamp when the brew log was last updated")

class EvaluationCreate(BaseModel):
    brew_log_id: int = Field(ge=1, description="Reference to brew_logs.id")
    confidence: int = Field(ge=1, le=3, description="Confidence level from 1 to 3")
    overall_score: int | None = Field(default=None, ge=1, le=10, description="Overall score from 1 to 10")
    taste_defect: Literal["none", "thin", "sour", "bitter", "not_sweet"] = Field(description="Type of taste defect")
    aroma_defect: bool = Field(description="Whether there is an aroma defect")
    aftertaste_defect: bool = Field(description="Whether there is an aftertaste defect")
    texture_defect: bool = Field(description="Whether there is a texture defect")
    memo: str | None = Field(default=None, description="Optional memo about the evaluation")

    @model_validator(mode="after")
    def check_evaluation_fields(self):
        if self.confidence in (2, 3) and self.overall_score is None:
            raise ValueError("overall_score is required when confidence is 2 or 3")
        return self

class EvaluationRead(EvaluationCreate):
    id: int = Field(description="Primary key")
    created_at: datetime = Field(description="Timestamp when the evaluation was created")
    updated_at: datetime = Field(description="Timestamp when the evaluation was last updated")

class ExternalBenchmarkCreate(BaseModel):
    consumed_at: date = Field(description="Date when the benchmark was consumed")
    source_type: Literal["cafe", "convenience_store", "other"] = Field(description="Source type of the benchmark")
    product_name: str = Field(min_length=1, description="Product name of the benchmark")
    overall_score: int = Field(ge=1, le=10, description="Overall score from 1 to 10")
    note: str | None = Field(default=None, description="Optional note about the benchmark")
    
class ExternalBenchmarkRead(ExternalBenchmarkCreate):
    id: int = Field(description="Primary key")
    created_at: datetime = Field(description="Timestamp when the benchmark was created")
    updated_at: datetime = Field(description="Timestamp when the benchmark was last updated")