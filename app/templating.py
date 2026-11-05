from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import APP_TIMEZONE

PROJECT_ROOT = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")


def local_datetime(value: datetime | None) -> str:
    """UTC from the API, shown in the user's local time."""
    if value is None:
        return "—"
    return value.astimezone(APP_TIMEZONE).strftime("%Y-%m-%d %H:%M")


def number(value: float | int | None, digits: int = 2) -> str:
    """Fixed decimals for display; the API itself returns unrounded values."""
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


templates.env.filters["local_datetime"] = local_datetime
templates.env.filters["number"] = number
