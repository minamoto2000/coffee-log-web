"""Comparison logic checked against values computed by hand (01b 1.2, 7.4)."""
import math
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.comparison import METRICS, TrialData, compare
from app.domain.experiment import (
    DEVIATED_OR_EXCLUDED,
    MEASUREMENT_REPEATS_MISSING,
    N_SMALL,
    NOT_BLINDED,
    ORDER_CONFOUNDED,
    ComparisonWarning,
)

T0 = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)


def trial(label, trial_id, hour, readings, beverage, *, overall=7, acidity=3, blinded=True,
          followed_plan=True, excluded=False, brew_time=200):
    return TrialData(
        condition_label=label,
        trial_id=trial_id,
        trial_no=trial_id,
        brewed_at=T0 + timedelta(hours=hour),
        followed_plan=followed_plan,
        excluded=excluded,
        dose_g_actual=15.0,
        beverage_mass_g=beverage,
        brew_time_s=brew_time,
        tds_readings_pct=tuple(readings),
        sensory={"overall_score": overall, "acidity": acidity, "sweetness": None, "bitterness": None,
                 "body": None, "aroma": None, "blinded": blinded},
    )


def acceptance_trials():
    """50 C (A) and 93 C (B) bloom, 3 trials each, alternating, TDS read twice."""
    return [
        trial("A", 1, 0, [1.30, 1.32], 212, overall=6, acidity=3),
        trial("B", 2, 1, [1.40, 1.42], 210, overall=7, acidity=4),
        trial("A", 3, 2, [1.34, 1.34], 213, overall=7, acidity=3),
        trial("B", 4, 3, [1.44, 1.44], 211, overall=8, acidity=3),
        trial("A", 5, 4, [1.28, 1.30], 211, overall=6, acidity=2),
        trial("B", 6, 5, [1.38, 1.40], 212, overall=7, acidity=4),
    ]


def sample_sd(values):
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def test_acceptance_scenario_tds_and_spread():
    result = compare(acceptance_trials(), diff_count=1, extraction_style="percolation")
    a, b = result.conditions["A"], result.conditions["B"]

    a_means, b_means = [1.31, 1.34, 1.29], [1.41, 1.44, 1.39]
    assert a.included_trial_count == b.included_trial_count == 3
    assert [v.value for v in a.metrics["tds_pct"].values] == pytest.approx(a_means)
    assert a.metrics["tds_pct"].summary.mean == pytest.approx(sum(a_means) / 3)
    assert a.metrics["tds_pct"].summary.sd == pytest.approx(sample_sd(a_means))
    assert result.differences["tds_pct"] == pytest.approx(0.10)

    # between-trial spread: SD of the per-trial means
    assert a.between_trial_sd.sd == pytest.approx(sample_sd(a_means))
    assert b.between_trial_sd.sd == pytest.approx(sample_sd(b_means))
    # measurement spread: within-trial variances 0.0002, 0, 0.0002, one df each
    assert a.measurement_sd.value == pytest.approx(math.sqrt(0.0004 / 3))
    assert a.measurement_sd.degrees_of_freedom == 3


def test_acceptance_scenario_ey_and_sensory():
    result = compare(acceptance_trials(), diff_count=1, extraction_style="percolation")
    a, b = result.conditions["A"], result.conditions["B"]

    a_ey = [1.31 * 212 / 15, 1.34 * 213 / 15, 1.29 * 211 / 15]
    b_ey = [1.41 * 210 / 15, 1.44 * 211 / 15, 1.39 * 212 / 15]
    assert [v.value for v in a.metrics["ey_pct"].values] == pytest.approx(a_ey)
    assert result.differences["ey_pct"] == pytest.approx(sum(b_ey) / 3 - sum(a_ey) / 3)
    assert a.metrics["overall_score"].summary.median == 6
    assert b.metrics["overall_score"].summary.median == 7
    assert result.differences["overall_score"] == pytest.approx(22 / 3 - 19 / 3)
    assert a.metrics["sweetness"].summary.n == 0
    assert result.differences["sweetness"] is None


def test_acceptance_scenario_warns_only_about_small_n():
    result = compare(acceptance_trials(), diff_count=1, extraction_style="percolation")

    assert result.warnings == [ComparisonWarning(N_SMALL)]
    assert set(result.differences) == set(METRICS)


def test_values_are_in_brewing_order():
    trials = list(reversed(acceptance_trials()))

    result = compare(trials, diff_count=1, extraction_style="percolation")

    assert [v.trial_id for v in result.conditions["A"].metrics["tds_pct"].values] == [1, 3, 5]


def test_excluded_and_deviated_trials_are_omitted_by_default():
    trials = acceptance_trials() + [
        trial("A", 7, 6, [2.0], 200, excluded=True),
        trial("B", 8, 7, [2.0], 200, followed_plan=False),
    ]

    default = compare(trials, diff_count=1, extraction_style="percolation")
    with_deviated = compare(trials, diff_count=1, extraction_style="percolation", include_deviated=True)

    assert default.conditions["B"].included_trial_count == 3
    assert ComparisonWarning(DEVIATED_OR_EXCLUDED, count=2) in default.warnings
    assert with_deviated.conditions["B"].included_trial_count == 4
    assert with_deviated.conditions["A"].included_trial_count == 3  # excluded never counts
    assert ComparisonWarning(DEVIATED_OR_EXCLUDED, count=1) in with_deviated.warnings


def test_blocked_order_is_warned():
    trials = [
        trial("A", 1, 0, [1.3, 1.3], 212),
        trial("A", 2, 1, [1.3, 1.3], 212),
        trial("B", 3, 2, [1.4, 1.4], 212),
        trial("B", 4, 3, [1.4, 1.4], 212),
    ]

    assert ComparisonWarning(ORDER_CONFOUNDED) in compare(trials, diff_count=1, extraction_style="percolation").warnings


def test_unblinded_and_single_readings_are_warned():
    trials = [trial("A", 1, 0, [1.3], 212, blinded=False), trial("B", 2, 1, [1.4], 212)]

    warnings = compare(trials, diff_count=1, extraction_style="percolation").warnings

    assert ComparisonWarning(NOT_BLINDED) in warnings
    assert ComparisonWarning(MEASUREMENT_REPEATS_MISSING) in warnings


def test_trials_without_tds_are_left_out_of_tds_metrics_only():
    trials = [trial("A", 1, 0, [], 212), trial("A", 2, 1, [1.3, 1.32], 212)]

    a = compare(trials, diff_count=1, extraction_style="percolation").conditions["A"]

    assert a.included_trial_count == 2
    assert a.metrics["tds_pct"].summary.n == 1
    assert a.metrics["ey_pct"].summary.n == 1
    assert a.metrics["beverage_mass_g"].summary.n == 2
    assert a.between_trial_sd.sd is None  # one TDS mean is not a spread


def test_no_trials():
    result = compare([], diff_count=1, extraction_style="percolation")

    assert result.conditions["A"].included_trial_count == 0
    assert result.conditions["A"].measurement_sd.value is None
    assert all(value is None for value in result.differences.values())
