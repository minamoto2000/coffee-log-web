"""Condition comparison (01b 7.4).

Descriptive only: values, n, mean, SD, median, range, the B - A mean
difference and warning codes. No test statistic and no "effect" verdict.
"""
from dataclasses import dataclass
from datetime import datetime

from app.domain.experiment import (
    LABELS,
    ComparisonWarning,
    collect_warnings,
    is_order_confounded,
)
from app.domain.stats import PooledSd, Summary, pooled_sd, summarize
from app.domain.trial import trial_measures

ATTRIBUTES = ("acidity", "sweetness", "bitterness", "body", "aroma")
SENSORY_METRICS = ("overall_score", *ATTRIBUTES)
METRICS = ("tds_pct", "ey_pct", "beverage_mass_g", "brew_time_s", *SENSORY_METRICS)


@dataclass(frozen=True)
class TrialData:
    condition_label: str
    trial_id: int
    trial_no: int
    brewed_at: datetime
    followed_plan: bool
    excluded: bool
    dose_g_actual: float
    beverage_mass_g: float | None
    brew_time_s: int | None
    tds_readings_pct: tuple[float, ...]
    sensory: dict | None  # overall_score, the attributes and blinded


@dataclass(frozen=True)
class MetricValue:
    trial_id: int
    trial_no: int
    brewed_at: datetime
    value: float


@dataclass(frozen=True)
class MetricSummary:
    values: list[MetricValue]
    summary: Summary


@dataclass(frozen=True)
class ConditionComparison:
    label: str
    included_trial_count: int
    metrics: dict[str, MetricSummary]
    measurement_sd: PooledSd  # repeated readings of the same beverage
    between_trial_sd: Summary  # spread of per-trial TDS means


@dataclass(frozen=True)
class Comparison:
    include_deviated: bool
    conditions: dict[str, ConditionComparison]
    differences: dict[str, float | None]
    omitted_trial_count: int
    warnings: list[ComparisonWarning]


def is_included(trial: TrialData, include_deviated: bool) -> bool:
    """Excluded trials never count. Deviated trials count only on request."""
    return not trial.excluded and (include_deviated or trial.followed_plan)


def metric_values(trial: TrialData) -> dict[str, float | None]:
    measures = trial_measures(list(trial.tds_readings_pct), trial.beverage_mass_g, trial.dose_g_actual)
    values = {
        "tds_pct": measures.tds.mean,
        "ey_pct": measures.ey.value,
        "beverage_mass_g": trial.beverage_mass_g,
        "brew_time_s": trial.brew_time_s,
    }
    for name in SENSORY_METRICS:
        values[name] = trial.sensory.get(name) if trial.sensory else None
    return values


def compare(
    trials: list[TrialData],
    *,
    diff_count: int,
    extraction_style: str,
    include_deviated: bool = False,
) -> Comparison:
    ordered = sorted(trials, key=lambda trial: (trial.brewed_at, trial.trial_id))
    included = [trial for trial in ordered if is_included(trial, include_deviated)]

    conditions = {
        label: _condition([trial for trial in included if trial.condition_label == label], label)
        for label in LABELS
    }
    differences = {
        name: _mean_difference(conditions["A"].metrics[name].summary, conditions["B"].metrics[name].summary)
        for name in METRICS
    }

    def times(label: str) -> list[datetime]:
        return [trial.brewed_at for trial in included if trial.condition_label == label]

    omitted = len(ordered) - len(included)
    warnings = collect_warnings(
        n_by_condition={label: conditions[label].included_trial_count for label in LABELS},
        order_confounded=is_order_confounded(times("A"), times("B")),
        diff_count=diff_count,
        any_not_blinded=any(trial.sensory is not None and not trial.sensory["blinded"] for trial in included),
        omitted_trial_count=omitted,
        has_measurement_repeats=any(len(trial.tds_readings_pct) >= 2 for trial in included),
        extraction_style=extraction_style,
    )
    return Comparison(
        include_deviated=include_deviated,
        conditions=conditions,
        differences=differences,
        omitted_trial_count=omitted,
        warnings=warnings,
    )


def _condition(trials: list[TrialData], label: str) -> ConditionComparison:
    per_trial = [(trial, metric_values(trial)) for trial in trials]
    metrics = {}
    for name in METRICS:
        values = [
            MetricValue(trial.trial_id, trial.trial_no, trial.brewed_at, value[name])
            for trial, value in per_trial
            if value[name] is not None
        ]
        metrics[name] = MetricSummary(values=values, summary=summarize([item.value for item in values]))
    return ConditionComparison(
        label=label,
        included_trial_count=len(trials),
        metrics=metrics,
        measurement_sd=pooled_sd([list(trial.tds_readings_pct) for trial in trials]),
        between_trial_sd=metrics["tds_pct"].summary,
    )


def _mean_difference(a: Summary, b: Summary) -> float | None:
    if a.mean is None or b.mean is None:
        return None
    return b.mean - a.mean
