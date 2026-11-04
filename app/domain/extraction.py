"""Extraction yield (01a 2.1, 01b 7.3).

Only the beverage-mass method is implemented in the MVP. It ignores the
liquid retained in the grounds, which is acceptable for percolation but
underestimates EY for immersion and hybrid brewers.
"""
from dataclasses import dataclass, field

BEVERAGE_MASS_V1 = "BEVERAGE_MASS_V1"

NO_TDS_READING = "NO_TDS_READING"
NO_BEVERAGE_MASS = "NO_BEVERAGE_MASS"

PERCOLATION_RETAINED_LIQUID_IGNORED = "PERCOLATION_RETAINED_LIQUID_IGNORED"


@dataclass(frozen=True)
class EyResult:
    value: float | None  # percent
    method: str
    inputs: dict
    assumptions: list[str] = field(default_factory=list)
    null_reason: str | None = None


def ey_beverage_mass(
    tds_mean_pct: float | None,
    beverage_mass_g: float | None,
    dose_g_actual: float,
) -> EyResult:
    """EY(%) = TDS(%) x beverage mass(g) / actual dose(g).

    Both TDS and EY are percentages, so no unit conversion is needed.
    The planned dose is never used as a substitute for the actual dose.
    """
    if dose_g_actual <= 0:
        raise ValueError("dose_g_actual must be positive")

    inputs = {
        "tds_mean_pct": tds_mean_pct,
        "beverage_mass_g": beverage_mass_g,
        "dose_g_actual": dose_g_actual,
    }
    assumptions = [PERCOLATION_RETAINED_LIQUID_IGNORED]

    if tds_mean_pct is None:
        return EyResult(None, BEVERAGE_MASS_V1, inputs, assumptions, NO_TDS_READING)
    if beverage_mass_g is None:
        return EyResult(None, BEVERAGE_MASS_V1, inputs, assumptions, NO_BEVERAGE_MASS)

    return EyResult(
        value=tds_mean_pct * beverage_mass_g / dose_g_actual,
        method=BEVERAGE_MASS_V1,
        inputs=inputs,
        assumptions=assumptions,
    )
