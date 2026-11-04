import pytest

from app.domain.extraction import (
    BEVERAGE_MASS_V1,
    NO_BEVERAGE_MASS,
    NO_TDS_READING,
    PERCOLATION_RETAINED_LIQUID_IGNORED,
    ey_beverage_mass,
)


def test_ey_matches_spec_example():
    result = ey_beverage_mass(tds_mean_pct=1.39, beverage_mass_g=212.4, dose_g_actual=15.02)

    assert result.value == pytest.approx(19.656, abs=0.001)
    assert result.method == BEVERAGE_MASS_V1
    assert result.null_reason is None
    assert result.inputs == {"tds_mean_pct": 1.39, "beverage_mass_g": 212.4, "dose_g_actual": 15.02}
    assert result.assumptions == [PERCOLATION_RETAINED_LIQUID_IGNORED]


def test_ey_without_tds_is_null_with_reason():
    result = ey_beverage_mass(tds_mean_pct=None, beverage_mass_g=212.4, dose_g_actual=15.0)

    assert result.value is None
    assert result.null_reason == NO_TDS_READING


def test_ey_without_beverage_mass_is_null_with_reason():
    result = ey_beverage_mass(tds_mean_pct=1.4, beverage_mass_g=None, dose_g_actual=15.0)

    assert result.value is None
    assert result.null_reason == NO_BEVERAGE_MASS


def test_ey_reports_missing_tds_first_when_both_are_missing():
    result = ey_beverage_mass(tds_mean_pct=None, beverage_mass_g=None, dose_g_actual=15.0)

    assert result.null_reason == NO_TDS_READING


def test_ey_scales_with_actual_dose_not_planned_dose():
    heavier = ey_beverage_mass(tds_mean_pct=1.4, beverage_mass_g=210, dose_g_actual=15.5)
    lighter = ey_beverage_mass(tds_mean_pct=1.4, beverage_mass_g=210, dose_g_actual=14.5)

    assert heavier.value < lighter.value


@pytest.mark.parametrize("dose", [0, -1])
def test_ey_rejects_non_positive_dose(dose):
    with pytest.raises(ValueError):
        ey_beverage_mass(tds_mean_pct=1.4, beverage_mass_g=210, dose_g_actual=dose)
