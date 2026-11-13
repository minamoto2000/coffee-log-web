"""Assemble the condition comparison from stored trials (01b 7.4)."""
from contextlib import closing
from datetime import datetime

from app.db import get_connection
from app.domain.comparison import SENSORY_METRICS, TrialData, compare
from app.errors import NotFoundError
from app.repositories import experiments as repository
from app.schemas.comparison import (
    ComparisonRead,
    ConditionComparisonRead,
    DifferenceRead,
    MetricRead,
    MetricValueRead,
    PooledSdRead,
    SpreadRead,
    TdsVariabilityRead,
    WarningRead,
)
from app.services.experiments import EXPERIMENT_NOT_FOUND, plan_diff


def get(experiment_id: int, include_deviated: bool = False) -> ComparisonRead:
    with closing(get_connection()) as conn:
        experiment = repository.find_experiment(conn, experiment_id)
        if experiment is None:
            raise NotFoundError(EXPERIMENT_NOT_FOUND)

        conditions = {row["label"]: row for row in repository.list_conditions(conn, experiment_id)}
        rows = repository.list_trials_for_experiment(conn, experiment_id)
        trial_ids = [row["id"] for row in rows]
        readings = repository.tds_readings_by_trial(conn, trial_ids)
        sensory = repository.sensory_by_trial(conn, trial_ids)
        diff = plan_diff(conn, experiment_id)

    trials = [
        TrialData(
            condition_label=row["condition_label"],
            trial_id=row["id"],
            trial_no=row["trial_no"],
            brewed_at=datetime.fromisoformat(row["brewed_at"]),
            followed_plan=bool(row["followed_plan"]),
            excluded=bool(row["excluded"]),
            dose_g_actual=row["dose_g_actual"],
            beverage_mass_g=row["beverage_mass_g"],
            brew_time_s=row["brew_time_s"],
            tds_readings_pct=tuple(readings[row["id"]]),
            sensory=_sensory(sensory.get(row["id"])),
        )
        for row in rows
    ]
    result = compare(
        trials,
        diff_count=len(diff),
        extraction_style=experiment["extraction_style"],
        include_deviated=include_deviated,
    )

    return ComparisonRead(
        experiment_id=experiment_id,
        include_deviated=include_deviated,
        conditions=[
            ConditionComparisonRead(
                label=label,
                condition_id=conditions[label]["id"],
                name=conditions[label]["name"],
                included_trial_count=condition.included_trial_count,
                metrics={
                    name: MetricRead(
                        n=metric.summary.n,
                        values=[MetricValueRead(**vars(value)) for value in metric.values],
                        mean=metric.summary.mean,
                        sd=metric.summary.sd,
                        median=metric.summary.median,
                        min=metric.summary.min,
                        max=metric.summary.max,
                    )
                    for name, metric in condition.metrics.items()
                },
            )
            for label, condition in result.conditions.items()
        ],
        tds_variability={
            label: TdsVariabilityRead(
                measurement_sd=PooledSdRead(**vars(condition.measurement_sd)),
                between_trial_sd=SpreadRead(value=condition.between_trial_sd.sd, n=condition.between_trial_sd.n),
            )
            for label, condition in result.conditions.items()
        },
        differences={name: DifferenceRead(mean_b_minus_a=value) for name, value in result.differences.items()},
        warnings=[WarningRead(code=warning.code, count=warning.count) for warning in result.warnings],
    )


def _sensory(row) -> dict | None:
    if row is None:
        return None
    values = {name: row[name] for name in SENSORY_METRICS}
    values["blinded"] = bool(row["blinded"])
    return values
