"""Experiment-level derived values: status, next condition, order confounding, warnings.

See 01b section 5 (status, next condition) and 7.4 (warning codes).
"""
from dataclasses import dataclass
from datetime import datetime

LABELS = ("A", "B")

DRAFT = "DRAFT"
RUNNING = "RUNNING"
PLANNED_REACHED = "PLANNED_REACHED"

N_SMALL_THRESHOLD = 5  # operational default, not a statistical threshold


@dataclass(frozen=True)
class TrialRef:
    """The minimum a derivation needs to know about one trial."""

    condition_label: str
    trial_id: int
    brewed_at: datetime
    excluded: bool = False


def _counted(trials: list[TrialRef]) -> list[TrialRef]:
    return [trial for trial in trials if not trial.excluded]


def experiment_status(trials: list[TrialRef], planned_trials_per_condition: int) -> str:
    """DRAFT = no trials at all (the plan is still editable).

    PLANNED_REACHED = every condition has at least the planned number of
    non-excluded trials. Otherwise RUNNING.
    """
    if not trials:
        return DRAFT
    counted = _counted(trials)
    if all(
        sum(1 for trial in counted if trial.condition_label == label) >= planned_trials_per_condition
        for label in LABELS
    ):
        return PLANNED_REACHED
    return RUNNING


def next_condition_label(trials: list[TrialRef]) -> str:
    """Condition with fewer non-excluded trials; on a tie, the opposite of the
    most recent trial (by brewed_at, id); with no trials, A.
    """
    counted = _counted(trials)
    counts = {label: sum(1 for trial in counted if trial.condition_label == label) for label in LABELS}
    if counts["A"] != counts["B"]:
        return "A" if counts["A"] < counts["B"] else "B"
    if not trials:
        return "A"
    latest = max(trials, key=lambda trial: (trial.brewed_at, trial.trial_id))
    return "B" if latest.condition_label == "A" else "A"


def is_order_confounded(times_a: list[datetime], times_b: list[datetime]) -> bool:
    """True when both conditions have >= 2 trials and all trials of one
    condition were brewed before all trials of the other.
    """
    if len(times_a) < 2 or len(times_b) < 2:
        return False
    return max(times_a) < min(times_b) or max(times_b) < min(times_a)


# Warning codes, in the order of the table in 01b 7.4.
N_SMALL = "N_SMALL"
ORDER_CONFOUNDED = "ORDER_CONFOUNDED"
MULTIPLE_VARIABLES_CHANGED = "MULTIPLE_VARIABLES_CHANGED"
NO_DIFFERENCE_IN_PLAN = "NO_DIFFERENCE_IN_PLAN"
NOT_BLINDED = "NOT_BLINDED"
DEVIATED_OR_EXCLUDED = "DEVIATED_OR_EXCLUDED"
MEASUREMENT_REPEATS_MISSING = "MEASUREMENT_REPEATS_MISSING"
EY_METHOD_ASSUMPTION = "EY_METHOD_ASSUMPTION"


@dataclass(frozen=True)
class ComparisonWarning:
    code: str
    count: int | None = None


def collect_warnings(
    *,
    n_by_condition: dict[str, int],
    order_confounded: bool,
    diff_count: int,
    any_not_blinded: bool,
    omitted_trial_count: int,
    has_measurement_repeats: bool,
    extraction_style: str,
) -> list[ComparisonWarning]:
    warnings: list[ComparisonWarning] = []
    if any(n_by_condition.get(label, 0) < N_SMALL_THRESHOLD for label in LABELS):
        warnings.append(ComparisonWarning(N_SMALL))
    if order_confounded:
        warnings.append(ComparisonWarning(ORDER_CONFOUNDED))
    if diff_count >= 2:
        warnings.append(ComparisonWarning(MULTIPLE_VARIABLES_CHANGED))
    if diff_count == 0:
        warnings.append(ComparisonWarning(NO_DIFFERENCE_IN_PLAN))
    if any_not_blinded:
        warnings.append(ComparisonWarning(NOT_BLINDED))
    if omitted_trial_count > 0:
        warnings.append(ComparisonWarning(DEVIATED_OR_EXCLUDED, count=omitted_trial_count))
    if not has_measurement_repeats:
        warnings.append(ComparisonWarning(MEASUREMENT_REPEATS_MISSING))
    if extraction_style != "percolation":
        warnings.append(ComparisonWarning(EY_METHOD_ASSUMPTION))
    return warnings
