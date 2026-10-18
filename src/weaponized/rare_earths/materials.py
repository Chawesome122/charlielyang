"""Explicit mass-basis transformations; native units never disappear silently."""
from __future__ import annotations

import math

# Standard atomic weights; these constants suffice at project-capacity precision.
ATOMIC_MASS = {"Nd": 144.242, "Pr": 140.90766, "Dy": 162.500, "Tb": 158.92535, "O": 15.999}
OXIDE_FORMULAE = {"Nd2O3": {"Nd": 2, "O": 3}, "Pr6O11": {"Pr": 6, "O": 11},
                  "Pr2O3": {"Pr": 2, "O": 3}, "Dy2O3": {"Dy": 2, "O": 3},
                  "Tb4O7": {"Tb": 4, "O": 7}, "Tb2O3": {"Tb": 2, "O": 3}}


def oxide_element_fraction(formula: str, element: str) -> float:
    """Contained element tonnes per tonne of chemically specified pure oxide."""
    if formula not in OXIDE_FORMULAE:
        raise ValueError(f"Unknown oxide formula: {formula}; supply an evidenced composition")
    stoich = OXIDE_FORMULAE[formula]
    if element not in stoich or element == "O":
        raise ValueError(f"{element} is not a rare-earth constituent of {formula}")
    return stoich[element] * ATOMIC_MASS[element] / sum(ATOMIC_MASS[k] * n for k, n in stoich.items())


def oxide_to_element(mass: float, formula: str, element: str, recovery: float = 1.0,
                     purity: float = 1.0) -> float:
    """Convert a stated oxide mass through purity, stoichiometry and process recovery."""
    if not math.isfinite(mass) or mass < 0 or not 0 <= recovery <= 1 or not 0 <= purity <= 1:
        raise ValueError("Mass must be finite/nonnegative; purity and recovery must be in [0,1]")
    return mass * purity * recovery * oxide_element_fraction(formula, element)


def annual_to_quarter(capacity: float, *, convention: str, operating_day_fraction: float | None = None) -> float:
    """Require a declared temporal conversion instead of silently dividing by four."""
    if not math.isfinite(capacity) or capacity < 0:
        raise ValueError("Capacity must be finite and nonnegative")
    if convention == "uniform_calendar":
        if operating_day_fraction is not None:
            raise ValueError("Uniform calendar cannot also specify an operating-day fraction")
        return capacity / 4
    if convention == "operating_days" and operating_day_fraction is not None and 0 <= operating_day_fraction <= 1:
        return capacity * operating_day_fraction
    raise ValueError("Use uniform_calendar or operating_days with an explicit fraction")


def contained_elements(mass: float, composition: dict[str, float]) -> dict[str, float]:
    if not math.isfinite(mass) or mass < 0 or any(not math.isfinite(v) or v < 0 for v in composition.values()):
        raise ValueError("Finite nonnegative mass and composition required")
    if sum(composition.values()) > 1 + 1e-12:
        raise ValueError("Element mass fractions sum above one")
    return {e: mass * fraction for e, fraction in composition.items()}


def reported_batch_summary(oxide_input_tonnes: float, magnet_output_tonnes: float) -> dict:
    """Describe a finite reported batch without inventing process yield or rate.

    The numerator and denominator are different products; iron, boron and other
    inputs are not observed here. Product expansion above one is not element
    creation, and a batch is not an annual production capacity.
    """
    if any(not math.isfinite(x) or x <= 0 for x in [oxide_input_tonnes, magnet_output_tonnes]):
        raise ValueError("Finite positive reported batch amounts are required")
    return dict(oxide_input_tonnes=oxide_input_tonnes, magnet_output_tonnes=magnet_output_tonnes,
                magnet_to_oxide_product_mass_ratio=magnet_output_tonnes/oxide_input_tonnes,
                minimum_additional_input_mass_tonnes=max(0.0, magnet_output_tonnes-oxide_input_tonnes),
                additional_input_bound_basis="aggregate batch mass conservation; assumes nonnegative other outputs; reported masses are approximate",
                quantity_basis="total finite batch, not a rate",
                elemental_recovery_estimate=None, annual_capacity_estimate=None,
                china_free_service_estimate=None)
