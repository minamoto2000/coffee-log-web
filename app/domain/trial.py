"""Per-trial derived values (01b 3.7, 7.3)."""
from dataclasses import dataclass
from datetime import date, datetime, tzinfo

from app.domain.extraction import EyResult, ey_beverage_mass
from app.domain.stats import Summary, summarize


@dataclass(frozen=True)
class TrialMeasures:
    tds: Summary  # repeated readings of the same beverage
    ey: EyResult


def trial_measures(
    tds_readings_pct: list[float],
    beverage_mass_g: float | None,
    dose_g_actual: float,
) -> TrialMeasures:
    """TDS is the mean of the repeated readings; EY uses that mean."""
    tds = summarize(tds_readings_pct)
    return TrialMeasures(tds=tds, ey=ey_beverage_mass(tds.mean, beverage_mass_g, dose_g_actual))


def days_since_roast(roast_date: date | None, brewed_at: datetime, local_tz: tzinfo) -> int | None:
    """Calendar days between the roast date and the local brewing date.

    Negative when the brew is dated before the roast date (an input error
    the caller may want to show); not rejected here.
    """
    if roast_date is None:
        return None
    return (brewed_at.astimezone(local_tz).date() - roast_date).days
