import pytest

from app.domain.protocol import (
    MAX_STEPS,
    ConditionPlan,
    DiffItem,
    Step,
    condition_diff,
    planned_total_water_g,
    validate_steps,
)


def pour(start_s, water_g=50.0, kettle_temp_c=93.0, duration_s=None):
    return Step("pour", start_s, duration_s=duration_s, water_g=water_g, kettle_temp_c=kettle_temp_c)


def bloom_50c_plan():
    """Condition A of the acceptance scenario (01b 1.2)."""
    return [pour(0, 30, 50), pour(120, 100, 93), pour(150, 120, 93)]


def test_acceptance_scenario_steps_are_valid():
    assert validate_steps(bloom_50c_plan()) == []


def test_empty_steps_are_rejected():
    assert validate_steps([]) == [f"steps must contain 1 to {MAX_STEPS} items"]


def test_more_than_max_steps_are_rejected():
    steps = [pour(i * 10, water_g=1) for i in range(MAX_STEPS + 1)]

    assert f"steps must contain 1 to {MAX_STEPS} items" in validate_steps(steps)


def test_steps_without_pour_are_rejected():
    steps = [Step("agitate", 0, agitation_method="stir")]

    assert "steps must include at least one pour" in validate_steps(steps)


def test_first_pour_must_start_at_zero():
    errors = validate_steps([pour(5), pour(60)])

    assert errors == ["step 1: the first pour must start at 0 s (brew start)"]


def test_first_pour_is_found_after_non_pour_steps():
    steps = [Step("other", 0, label="rinse filter"), pour(0)]

    assert validate_steps(steps) == []


def test_start_times_must_not_decrease():
    errors = validate_steps([pour(0), pour(120), pour(60)])

    assert "step 3: start_s must not be earlier than step 2" in errors


def test_overlapping_pours_are_rejected():
    errors = validate_steps([pour(0, duration_s=30), pour(20)])

    assert errors == ["step 2: pour overlaps pour at step 1"]


def test_pour_may_start_exactly_when_previous_pour_ends():
    assert validate_steps([pour(0, duration_s=30), pour(30)]) == []


def test_agitation_may_overlap_a_pour():
    steps = [pour(0, duration_s=30), Step("agitate", 10, agitation_method="swirl"), pour(60)]

    assert validate_steps(steps) == []


def test_waiting_is_expressed_as_a_gap_not_a_step():
    # 0 s pour, wait until 120 s, then pour again
    assert validate_steps([pour(0), pour(120)]) == []


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        (Step("pour", 0, kettle_temp_c=93), "step 1: water_g is required for pour"),
        (Step("pour", 0, water_g=50), "step 1: kettle_temp_c is required for pour"),
        (
            Step("pour", 0, water_g=50, kettle_temp_c=93, label="x"),
            "step 1: label must be empty for pour",
        ),
        (Step("agitate", 0), "step 1: agitation_method is required for agitate"),
        (
            Step("agitate", 0, agitation_method="stir", water_g=10),
            "step 1: water_g must be empty for agitate",
        ),
        (Step("other", 0), "step 1: label is required for other"),
        (
            Step("other", 0, label="open valve", kettle_temp_c=90),
            "step 1: kettle_temp_c must be empty for other",
        ),
        (Step("wait", 0), "step 1: unknown step_type 'wait'"),
    ],
)
def test_type_specific_fields(step, expected):
    assert expected in validate_steps([step])


def test_condition_diff_of_acceptance_scenario_has_one_item():
    plan_a = ConditionPlan(15, 20, tuple(bloom_50c_plan()))
    plan_b = ConditionPlan(15, 20, (pour(0, 30, 93), pour(120, 100, 93), pour(150, 120, 93)))

    assert condition_diff(plan_a, plan_b) == [DiffItem("steps[1].kettle_temp_c", 50, 93)]


def test_condition_diff_reports_dose_grind_and_step_count():
    plan_a = ConditionPlan(15, 20, (pour(0),))
    plan_b = ConditionPlan(16, None, (pour(0), pour(60)))

    assert condition_diff(plan_a, plan_b) == [
        DiffItem("dose_g", 15, 16),
        DiffItem("grind_setting_value", 20, None),
        DiffItem("steps.count", 1, 2),
    ]


def test_condition_diff_ignores_notes():
    plan_a = ConditionPlan(15, 20, (Step("pour", 0, water_g=50, kettle_temp_c=93, note="slow"),))
    plan_b = ConditionPlan(15, 20, (Step("pour", 0, water_g=50, kettle_temp_c=93, note="fast"),))

    assert condition_diff(plan_a, plan_b) == []


def test_planned_total_water_counts_only_pours():
    steps = bloom_50c_plan() + [Step("agitate", 160, agitation_method="stir")]

    assert planned_total_water_g(steps) == 250
