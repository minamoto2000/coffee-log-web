from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


def normalize_stored_datetime(value: datetime) -> datetime:
    """Interpret a datetime read from SQLite as UTC.

    SQLite's CURRENT_TIMESTAMP is stored without an offset but is UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TimestampsRead(BaseModel):
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return normalize_stored_datetime(value)


def require_offset_utc(value: datetime) -> datetime:
    """Request datetimes must carry an offset; they are stored as UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone offset")
    return value.astimezone(timezone.utc)
