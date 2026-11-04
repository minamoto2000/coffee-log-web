"""Descriptive statistics used by trial-derived values and comparisons (01b 7.3, 7.4)."""
import math
from dataclasses import dataclass
from statistics import mean, median, stdev


@dataclass(frozen=True)
class Summary:
    n: int
    mean: float | None
    sd: float | None  # sample SD (n - 1); None when n < 2
    median: float | None
    min: float | None
    max: float | None


def summarize(values: list[float]) -> Summary:
    if not values:
        return Summary(n=0, mean=None, sd=None, median=None, min=None, max=None)
    return Summary(
        n=len(values),
        mean=mean(values),
        sd=stdev(values) if len(values) >= 2 else None,
        median=median(values),
        min=min(values),
        max=max(values),
    )


@dataclass(frozen=True)
class PooledSd:
    value: float | None
    groups_used: int  # groups with at least 2 values
    degrees_of_freedom: int


def pooled_sd(groups: list[list[float]]) -> PooledSd:
    """Within-group SD pooled across groups, weighted by degrees of freedom.

    Used for measurement repeatability: each group is the repeated TDS
    readings of one beverage. Groups with fewer than 2 values carry no
    information about within-group spread and are ignored.

    sqrt( sum((k_i - 1) * s_i^2) / sum(k_i - 1) )
    """
    usable = [group for group in groups if len(group) >= 2]
    degrees_of_freedom = sum(len(group) - 1 for group in usable)
    if degrees_of_freedom == 0:
        return PooledSd(value=None, groups_used=0, degrees_of_freedom=0)
    weighted = sum((len(group) - 1) * stdev(group) ** 2 for group in usable)
    return PooledSd(
        value=math.sqrt(weighted / degrees_of_freedom),
        groups_used=len(usable),
        degrees_of_freedom=degrees_of_freedom,
    )
