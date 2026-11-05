from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.extraction import NO_BEVERAGE_MASS
from app.domain.trial import days_since_roast, trial_measures

TOKYO = ZoneInfo("Asia/Tokyo")


def test_trial_measures_uses_mean_of_readings():
    measures = trial_measures([1.38, 1.40], 212.4, 15.02)

    assert measures.tds.mean == pytest.approx(1.39)
    assert measures.tds.n == 2
    assert measures.ey.value == pytest.approx(19.656, abs=0.001)


def test_trial_measures_without_beverage_mass():
    measures = trial_measures([1.4], None, 15.0)

    assert measures.tds.sd is None
    assert measures.ey.null_reason == NO_BEVERAGE_MASS


def test_days_since_roast_crosses_midnight_in_local_time():
    brewed_at = datetime(2026, 11, 4, 23, 30, tzinfo=timezone.utc)  # 2026-11-05 08:30 in Tokyo

    assert days_since_roast(date(2026, 10, 28), brewed_at, TOKYO) == 8
    assert days_since_roast(date(2026, 10, 28), brewed_at, timezone.utc) == 7


def test_days_since_roast_without_roast_date():
    assert days_since_roast(None, datetime(2026, 11, 5, tzinfo=timezone.utc), TOKYO) is None


def test_days_since_roast_before_roast_is_negative():
    assert days_since_roast(date(2026, 11, 6), datetime(2026, 11, 5, tzinfo=timezone.utc), TOKYO) == -1
