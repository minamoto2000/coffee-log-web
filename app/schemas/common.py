from datetime import datetime, timezone


def normalize_stored_datetime(value: datetime) -> datetime:
    """Interpret a datetime read from SQLite as UTC.

    SQLite's CURRENT_TIMESTAMP is stored without an offset but is UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
