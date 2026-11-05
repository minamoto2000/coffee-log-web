import math

import pytest

from app.domain.stats import pooled_sd, summarize


def test_summarize_empty_returns_all_none():
    summary = summarize([])

    assert summary.n == 0
    assert (summary.mean, summary.sd, summary.median, summary.min, summary.max) == (None,) * 5


def test_summarize_single_value_has_no_sd():
    summary = summarize([1.4])

    assert summary.n == 1
    assert summary.mean == 1.4
    assert summary.sd is None
    assert summary.median == 1.4


def test_summarize_uses_sample_sd_and_median():
    summary = summarize([3, 1, 2])

    assert summary.n == 3
    assert summary.mean == 2
    assert summary.sd == pytest.approx(1.0)  # sample SD (n - 1), not population
    assert summary.median == 2
    assert (summary.min, summary.max) == (1, 3)


def test_summarize_two_tds_readings():
    summary = summarize([1.38, 1.40])

    assert summary.mean == pytest.approx(1.39)
    assert summary.sd == pytest.approx(0.02 / math.sqrt(2))


def test_pooled_sd_ignores_groups_with_one_value():
    result = pooled_sd([[1.38, 1.40], [1.40, 1.44], [1.50]])

    # (1 * 0.0002 + 1 * 0.0008) / 2 = 0.0005
    assert result.value == pytest.approx(math.sqrt(0.0005))
    assert result.groups_used == 2
    assert result.degrees_of_freedom == 2


def test_pooled_sd_weights_by_degrees_of_freedom():
    result = pooled_sd([[1, 2, 3], [5, 7]])

    # variances 1 (df 2) and 2 (df 1): (2 * 1 + 1 * 2) / 3
    assert result.value == pytest.approx(math.sqrt(4 / 3))
    assert result.degrees_of_freedom == 3


def test_pooled_sd_without_repeats_is_none():
    result = pooled_sd([[1.4], [1.5], []])

    assert result.value is None
    assert result.groups_used == 0
