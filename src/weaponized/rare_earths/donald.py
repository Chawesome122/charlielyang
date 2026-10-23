"""Necessary four-element constraints from Donald's disclosed design assumptions.

These partial constraints stop at contained elements in mine concentrate. They do
not represent oxide separation, metal/alloy conversion, qualified magnets or a
measured stock. Normalized finite feeds are diagnostics, never empirical supply.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy.optimize import linprog

from weaponized.rare_earths.materials import oxide_element_fraction

OXIDES = {'Nd': 'Nd2O3', 'Pr': 'Pr6O11', 'Dy': 'Dy2O3', 'Tb': 'Tb4O7'}
GRADE_BASIS = 'oxide_mass_per_heavy_mineral_mass'


def nonnegative(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label}: finite nonnegative value required; unknown is not unlimited')
    return float(value)


def fraction(value, label):
    value = nonnegative(value, label)
    if value > 1:
        raise ValueError(f'{label}: fraction outside [0,1]')
    return value


def four_fractions(values: Mapping, label):
    if set(values) != set(OXIDES):
        raise ValueError(f'{label}: explicit Nd/Pr/Dy/Tb required')
    return {e: fraction(values[e], label + ':' + e) for e in OXIDES}


def nested_coefficients(hm_fraction, oxide_fractions, recovery_fractions, *, grade_basis):
    """Containment per dry bulk-ore tonne, using reserve HM-nested oxide grades."""
    if grade_basis != GRADE_BASIS:
        raise ValueError('Reserve oxide grades require the heavy-mineral denominator')
    hm = fraction(hm_fraction, 'HM mass fraction of bulk ore')
    grades = four_fractions(oxide_fractions, 'oxide share of HM')
    recovery = four_fractions(recovery_fractions, 'pit-design recovery to REEC')
    if sum(grades.values()) > 1 + 1e-12:
        raise ValueError('Joint oxide grades exceed HM mass')
    rows = []
    for e, formula in OXIDES.items():
        incoming = hm * grades[e] * oxide_element_fraction(formula, e)
        recovered = incoming * recovery[e]
        rows.append(dict(element=e, oxide=formula, hm_fraction=hm, oxide_fraction_of_HM=grades[e],
                         assumed_recovery=recovery[e], input_element_t_per_ore_t=incoming,
                         recovered_element_t_per_ore_t=recovered, residual_element_t_per_ore_t=incoming-recovered,
                         grade_basis=grade_basis, classification='conditional_reserve_and_pit_design_not_operating_yield'))
    return rows


def partial_recovery_lp(coefficients, feed_capacity, plant_feed_capacity, *, route_open=True, supplier_removed=False):
    """Maximize four contained outputs under ONE common finite feed constraint.

    Diagnostic tonnes are dry bulk ore. A closed route or failed owner removes
    the complete partial activity. This is a necessary process envelope, not an
    empirical route/plant capacity model or an end-to-end service optimization.
    """
    feed = nonnegative(feed_capacity, 'finite diagnostic feed')
    plant = nonnegative(plant_feed_capacity, 'declared diagnostic throughput limit')
    if not isinstance(route_open, bool) or not isinstance(supplier_removed, bool):
        raise ValueError('Explicit Boolean diagnostic route/outage state required')
    if len(coefficients) != 4 or {r['element'] for r in coefficients} != set(OXIDES):
        raise ValueError('One coefficient for each element required')
    by_element = {r['element']:r for r in coefficients}
    for r in coefficients:
        if r['grade_basis'] != GRADE_BASIS:
            raise ValueError('Partial LP cannot erase the reserve-grade denominator')
        incoming = nonnegative(r['input_element_t_per_ore_t'], 'input coefficient')
        recovered = nonnegative(r['recovered_element_t_per_ore_t'], 'output coefficient')
        if recovered > incoming + 1e-14:
            raise ValueError('Partial process creates contained element')
    if sum(r['input_element_t_per_ore_t'] for r in coefficients) > 1 + 1e-12:
        raise ValueError('Joint contained-element input exceeds one native ore tonne')
    coefs = np.array([by_element[e]['recovered_element_t_per_ore_t'] for e in OXIDES])
    capacity = min(feed, plant) if route_open and not supplier_removed else 0.
    # [q, d_Nd, d_Pr, d_Dy, d_Tb]; d_e <= a_e q.
    aub = np.column_stack((-coefs, np.eye(4)))
    objective = np.r_[0., -np.ones(4)]
    bounds = [(0., capacity)] + [(0., None)] * 4
    result = linprog(objective, A_ub=aub, b_ub=np.zeros(4), bounds=bounds, method='highs')
    if not result.success:
        raise RuntimeError('Partial finite-feed LP failed: ' + result.message)
    q = float(result.x[0]);d = result.x[1:]
    expected = capacity * coefs
    scale = max(1., float(expected.max(initial=0.)))
    tolerance = 1e-10 * scale
    max_error = float(abs(d-expected).max(initial=0.))
    losses = {e:q * by_element[e]['input_element_t_per_ore_t'] - float(d[i]) for i,e in enumerate(OXIDES)}
    # In this LP b_ub = lower bounds = zero; only q has a finite upper bound.
    dual_objective = capacity * float(result.upper.marginals[0])
    gap = abs(float(result.fun) - dual_objective)
    constraint_violation = float(np.maximum(aub @ result.x, 0.).max(initial=0.))
    return dict(passed=max_error<=tolerance and gap<=tolerance and constraint_violation<=tolerance and min(losses.values())>=-tolerance,
                classification='normalized_finite_feed_diagnostic_not_empirical_supply',
                finite_feed_tonnes=feed, plant_feed_limit_tonnes=plant, route_open=route_open, supplier_removed=supplier_removed,
                throughput_tonnes=q, output_element_tonnes=dict(zip(OXIDES,map(float,d))),
                residual_or_unrecovered_element_tonnes=losses, max_analytical_error_tonnes=max_error,
                max_constraint_violation_tonnes=constraint_violation, primal_dual_gap_tonnes=gap,
                empirical_inventory=False, empirical_route_capacity=False, delivered_magnet_service=None)


def conditional_reec_composition(treo_grade, distributions):
    """Financial-model composition on its as-stated basis, not an operating assay."""
    grade = fraction(treo_grade, 'TREO grade in REEC')
    shares = four_fractions(distributions, 'oxide fraction of TREO')
    if sum(shares.values()) > 1 + 1e-12:
        raise ValueError('Joint payable oxide shares exceed total TREO')
    return [dict(element=e, oxide=formula, oxide_share_of_TREO=shares[e], treo_grade=grade,
                 conditional_oxide_t_per_reec_t=grade*shares[e],
                 conditional_element_t_per_reec_t=grade*shares[e]*oxide_element_fraction(formula,e),
                 classification='financial_model_conditional_composition_not_available_feed',
                 moisture_basis_certified=False, annual_feed_available=None, delivered_magnet_service=None)
            for e,formula in OXIDES.items()]
