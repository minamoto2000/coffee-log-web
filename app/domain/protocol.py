"""Planned brewing steps: validation rules (01b 8.1) and condition diff (01b 7.5).

Waiting is not a step type: it is the gap between steps.
"""
from dataclasses import dataclass, fields

POUR = "pour"
AGITATE = "agitate"
OTHER = "other"
STEP_TYPES = (POUR, AGITATE, OTHER)

MAX_STEPS = 50


@dataclass(frozen=True)
class Step:
    step_type: str
    start_s: int
    duration_s: int | None = None
    water_g: float | None = None
    kettle_temp_c: float | None = None
    agitation_method: str | None = None
    label: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ConditionPlan:
    dose_g: float
    grind_setting_value: float | None
    steps: tuple[Step, ...]


def validate_steps(steps: list[Step]) -> list[str]:
    """Return every rule violation (empty list = valid).

    Field ranges (start_s >= 0, water_g > 0, ...) are checked by the
    request schema; this function checks the rules that span fields or rows.
    """
    errors: list[str] = []

    if not 1 <= len(steps) <= MAX_STEPS:
        errors.append(f"steps must contain 1 to {MAX_STEPS} items")
        if not steps:
            return errors

    for index, step in enumerate(steps, start=1):
        errors.extend(_type_rule_errors(index, step))

    for index in range(1, len(steps)):
        if steps[index].start_s < steps[index - 1].start_s:
            errors.append(f"step {index + 1}: start_s must not be earlier than step {index}")

    pours = [(index, step) for index, step in enumerate(steps, start=1) if step.step_type == POUR]
    if not pours:
        errors.append("steps must include at least one pour")
    else:
        first_index, first_pour = pours[0]
        if first_pour.start_s != 0:
            errors.append(f"step {first_index}: the first pour must start at 0 s (brew start)")
        for (prev_index, prev), (next_index, nxt) in zip(pours, pours[1:]):
            prev_end = prev.start_s + (prev.duration_s or 0)
            if prev_end > nxt.start_s:
                errors.append(f"step {next_index}: pour overlaps pour at step {prev_index}")

    return errors


def _type_rule_errors(index: int, step: Step) -> list[str]:
    if step.step_type not in STEP_TYPES:
        return [f"step {index}: unknown step_type {step.step_type!r}"]

    required = {
        POUR: ("water_g", "kettle_temp_c"),
        AGITATE: ("agitation_method",),
        OTHER: ("label",),
    }[step.step_type]
    type_specific = ("water_g", "kettle_temp_c", "agitation_method", "label")

    errors = []
    for name in required:
        if getattr(step, name) is None:
            errors.append(f"step {index}: {name} is required for {step.step_type}")
    for name in type_specific:
        if name not in required and getattr(step, name) is not None:
            errors.append(f"step {index}: {name} must be empty for {step.step_type}")
    return errors


@dataclass(frozen=True)
class DiffItem:
    path: str
    a: object
    b: object


STEP_COMPARED_FIELDS = tuple(f.name for f in fields(Step) if f.name != "note")


def condition_diff(a: ConditionPlan, b: ConditionPlan) -> list[DiffItem]:
    """Differences between two plans. Step paths use the 1-based seq.

    Notes are free text and are not compared. When step counts differ, the
    count is one item and only the common seq range is compared field by field.
    """
    items: list[DiffItem] = []
    if a.dose_g != b.dose_g:
        items.append(DiffItem("dose_g", a.dose_g, b.dose_g))
    if a.grind_setting_value != b.grind_setting_value:
        items.append(DiffItem("grind_setting_value", a.grind_setting_value, b.grind_setting_value))
    if len(a.steps) != len(b.steps):
        items.append(DiffItem("steps.count", len(a.steps), len(b.steps)))

    for seq, (step_a, step_b) in enumerate(zip(a.steps, b.steps), start=1):
        for name in STEP_COMPARED_FIELDS:
            value_a, value_b = getattr(step_a, name), getattr(step_b, name)
            if value_a != value_b:
                items.append(DiffItem(f"steps[{seq}].{name}", value_a, value_b))
    return items


def planned_total_water_g(steps: tuple[Step, ...] | list[Step]) -> float:
    return sum(step.water_g or 0 for step in steps if step.step_type == POUR)
