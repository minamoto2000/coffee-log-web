from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import normalize_stored_datetime

GrindSettingUnit = Literal["click", "step", "number", "other"]


class EquipmentSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Name of the equipment set")
    filter_label: str = Field(min_length=1, max_length=100, description="Label for the filter")
    brewer_label: str = Field(min_length=1, max_length=100, description="Label for the brewer")
    grinder_label: str = Field(min_length=1, max_length=100, description="Label for the grinder")
    grind_setting_unit: GrindSettingUnit = Field(description="Unit for the grind setting")
    note: str | None = Field(default=None, description="Optional note about the equipment")

    @field_validator("name", "filter_label", "brewer_label", "grinder_label", mode="before")
    @classmethod
    def trim_required_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class EquipmentSetRead(EquipmentSetCreate):
    id: int = Field(description="Primary key")
    is_active: bool = Field(description="Whether the equipment set is active")
    created_at: datetime = Field(description="Timestamp when the equipment set was created")
    updated_at: datetime = Field(description="Timestamp when the equipment set was last updated")

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)


class EquipmentSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100, description="Name of the equipment set")
    filter_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the filter")
    brewer_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the brewer")
    grinder_label: str | None = Field(default=None, min_length=1, max_length=100, description="Label for the grinder")
    grind_setting_unit: GrindSettingUnit | None = Field(default=None, description="Unit for the grind setting")
    note: str | None = Field(default=None, description="Optional note about the equipment")

    @field_validator("name", "filter_label", "brewer_label", "grinder_label", mode="before")
    @classmethod
    def trim_required_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name", "filter_label", "brewer_label", "grinder_label", "grind_setting_unit")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("field cannot be null")
        return value
