from datetime import datetime, timedelta, timezone

from app.domain.experiment import (
    DEVIATED_OR_EXCLUDED,
    DRAFT,
    EY_METHOD_ASSUMPTION,
    MEASUREMENT_REPEATS_MISSING,
    MULTIPLE_VARIABLES_CHANGED,
    N_SMALL,
    NO_DIFFERENCE_IN_PLAN,
    NOT_BLINDED,
    ORDER_CONFOUNDED,
    PLANNED_REACHED,
    RUNNING,
    ComparisonWarning,
    TrialRef,
    collect_warnings,
    experiment_status,
    is_order_confounded,
    next_condition_label,
)

T0 = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)


def at(hours):
    return T0 + timedelta(hours=hours)


def trial(label, trial_id, hours, excluded=False):
    return TrialRef(label, trial_id, at(hours), excluded)


def test_status_is_draft_without_trials():
    assert experiment_status([], planned_trials_per_condition=3) == DRAFT


def test_status_is_running_until_both_conditions_reach_plan():
    trials = [trial("A", 1, 0), trial("B", 2, 1), trial("A", 3, 2)]

    assert experiment_status(trials, planned_trials_per_condition=2) == RUNNING


def test_status_reaches_plan_when_every_condition_has_enough_trials():
    trials = [trial("A", 1, 0), trial("B", 2, 1), trial("B", 3, 2), trial("A", 4, 3)]

    assert experiment_status(trials, planned_trials_per_condition=2) == PLANNED_REACHED


def test_excluded_trials_do_not_count_towards_plan():
    trials = [trial("A", 1, 0), trial("B", 2, 1), trial("A", 3, 2), trial("B", 4, 3, excluded=True)]

    assert experiment_status(trials, planned_trials_per_condition=2) == RUNNING


def test_next_condition_is_a_without_trials():
    assert next_condition_label([]) == "A"


def test_next_condition_prefers_the_condition_with_fewer_trials():
    assert next_condition_label([trial("A", 1, 0), trial("A", 2, 1), trial("B", 3, 2)]) == "B"


def test_next_condition_alternates_on_a_tie():
    assert next_condition_label([trial("A", 1, 0), trial("B", 2, 1)]) == "A"
    assert next_condition_label([trial("B", 1, 0), trial("A", 2, 1)]) == "B"


def test_next_condition_tie_break_uses_id_for_same_time():
    assert next_condition_label([trial("B", 1, 0), trial("A", 2, 0)]) == "B"


def test_next_condition_ignores_excluded_trials_in_counts():
    trials = [trial("A", 1, 0), trial("B", 2, 1, excluded=True)]

    assert next_condition_label(trials) == "B"


def test_order_confounded_when_one_condition_entirely_precedes():
    assert is_order_confounded([at(0), at(1)], [at(2), at(3)])
    assert is_order_confounded([at(2), at(3)], [at(0), at(1)])


def test_interleaved_order_is_not_confounded():
    assert not is_order_confounded([at(0), at(2)], [at(1), at(3)])


def test_order_needs_two_trials_per_condition():
    assert not is_order_confounded([at(0)], [at(1), at(2)])


def baseline_warning_inputs(**overrides):
    inputs = dict(
        n_by_condition={"A": 5, "B": 5},
        order_confounded=False,
        diff_count=1,
        any_not_blinded=False,
        omitted_trial_count=0,
        has_measurement_repeats=True,
        extraction_style="percolation",
    )
    inputs.update(overrides)
    return inputs


def test_no_warnings_for_a_clean_single_variable_experiment():
    assert collect_warnings(**baseline_warning_inputs()) == []


def test_all_warnings_in_table_order():
    warnings = collect_warnings(
        **baseline_warning_inputs(
            n_by_condition={"A": 3, "B": 5},
            order_confounded=True,
            diff_count=2,
            any_not_blinded=True,
            omitted_trial_count=2,
            has_measurement_repeats=False,
            extraction_style="immersion",
        )
    )

    assert warnings == [
        ComparisonWarning(N_SMALL),
        ComparisonWarning(ORDER_CONFOUNDED),
        ComparisonWarning(MULTIPLE_VARIABLES_CHANGED),
        ComparisonWarning(NOT_BLINDED),
        ComparisonWarning(DEVIATED_OR_EXCLUDED, count=2),
        ComparisonWarning(MEASUREMENT_REPEATS_MISSING),
        ComparisonWarning(EY_METHOD_ASSUMPTION),
    ]


def test_no_difference_in_plan_warning():
    assert collect_warnings(**baseline_warning_inputs(diff_count=0)) == [
        ComparisonWarning(NO_DIFFERENCE_IN_PLAN)
    ]


def test_missing_condition_counts_as_small():
    assert ComparisonWarning(N_SMALL) in collect_warnings(
        **baseline_warning_inputs(n_by_condition={"A": 5})
    )
