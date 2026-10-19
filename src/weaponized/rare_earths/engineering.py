"""Partial oxide-equivalent accounting, never a complete industrial recipe.

This module does not assign an Nd/Pr split, product purity, calendar throughput,
ore extraction, routes, inventory, demand, or China-free qualification.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

from scipy.optimize import linprog


def _fraction(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite fraction in [0, 1]")
    return float(value)


def grouped_oxide_constraint(grade: float, distribution: Mapping[str, float],
                             recovery: float, *, product: str,
                             input_basis: str, output_basis: str) -> dict:
    """Recover one joint product group from a declared oxide-equivalent basis.

    Composition is conditional on total REO, whereas grade is conditional on
    bulk concentrate. Their denominators differ. The coefficient is an issuer
    assumption when its inputs are assumptions, not an empirical yield estimate.
    Other co-products and waste remain outside this necessary partial constraint.
    """
    if input_basis != "tonne_native_concentrate" or output_basis != "tonne_REO_equivalent":
        raise ValueError("Explicit concentrate input and oxide-equivalent output bases required")
    if not distribution or product not in distribution:
        raise ValueError("A complete named joint REO distribution is required")
    composition = {key: _fraction(value, key) for key, value in distribution.items()}
    if not math.isclose(sum(composition.values()), 1.0, abs_tol=1e-10):
        raise ValueError("Joint REO distribution must sum to one, without double counting")
    grade = _fraction(grade, "concentrate grade")
    recovery = _fraction(recovery, "recovery")
    available = grade * composition[product]
    coefficient = available * recovery
    return dict(product=product, input_basis=input_basis, output_basis=output_basis,
                grade=grade, product_share_of_REO=composition[product], recovery=recovery,
                input_product_REO_equivalent_per_native_tonne=available,
                recovered_product_REO_equivalent_per_native_tonne=coefficient,
                unrecovered_product_REO_equivalent_per_native_tonne=available-coefficient,
                joint_REO_fraction=sum(composition.values()),
                constraint_class="necessary_partial_material_constraint",
                observed_operating_yield=False, full_recipe_identified=False,
                elemental_Nd_Pr_split=None, physical_sale_product_mass=None,
                annual_output=None, finite_available_feed=None, China_free_service=None)


def normalized_finite_feed_check(coefficient: float, finite_feed: float) -> dict:
    """Independent LP check of a normalized partial constraint, not a forecast.

    `finite_feed` is an explicitly supplied diagnostic input, not empirical stock.
    Both zero and positive feeds are useful checks against free upstream material.
    Variables are native concentrate processed and recovered grouped REO output.
    """
    coefficient = _fraction(coefficient, "output coefficient")
    if not math.isfinite(finite_feed) or finite_feed < 0:
        raise ValueError("Diagnostic feed must be finite and nonnegative")
    result = linprog([0., -1.], A_ub=[[-coefficient, 1.]], b_ub=[0.],
                     bounds=[(0., finite_feed), (0., None)], method="highs")
    if not result.success:
        raise RuntimeError(result.message)
    output = float(result.x[1])
    expected = coefficient * finite_feed
    residual = abs(output-expected)
    if residual > 1e-10 * max(1., expected):
        raise ValueError("Partial material LP disagrees with the analytical bound")
    return dict(finite_diagnostic_feed=finite_feed, output_upper_bound=output,
                analytical_upper_bound=expected, bound_residual=residual,
                status=int(result.status), passed=True,
                evidence_class="normalized_engineering_diagnostic_not_industrial_supply")
