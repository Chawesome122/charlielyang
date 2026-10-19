"""Accounting identities and prospective product comparisons, not service y."""
import math


def cash_reconciliation(ppe, intangible, total_additions, capital_working_capital, cash_payments):
    """Signed reported reconciliation amounts in one common currency/duration."""
    values = [ppe, intangible, total_additions, capital_working_capital, cash_payments]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("Finite accounting amounts required")
    first, second = ppe+intangible-total_additions, total_additions+capital_working_capital-cash_payments
    return dict(additions_identity_residual=first, cash_identity_residual=second,
                passed=abs(first) <= 1 and abs(second) <= 1,
                project_allocation_identified=False, physical_output_inferred=False)


def facility_reconciliation(limit, drawn, undrawn):
    if not all(math.isfinite(x) and x >= 0 for x in [limit, drawn, undrawn]) or limit == 0:
        raise ValueError("Positive facility limit and finite nonnegative reported balances required")
    residual = limit-drawn-undrawn
    return dict(limit_identity_residual=residual, passed=abs(residual) <= 1e-8,
                precision_basis="identity on reported rounded balances, not a confidence interval for underlying amounts",
                undrawn_is_cash=False, borrowing_change_is_project_cash_capex=False,
                eligibility_and_draw_sequence_must_be_reviewed=True)


def planned_capacity_retention(base, expanded, *, product_base, product_expanded, unit_base, unit_expanded):
    """A within-product comparison of the same disclosed prospective basis.

    A native quantity basis may lack an explicit annual denominator. Ratios do
    not introduce one, recover element splits, trace origin or solve a network.
    """
    if not product_base or product_base != product_expanded or not unit_base or unit_base != unit_expanded:
        raise ValueError("Product and native quantity basis must agree within a comparison")
    if not math.isfinite(base) or not math.isfinite(expanded) or not 0 <= base <= expanded or expanded <= 0:
        raise ValueError("Require finite nonnegative base <= positive expanded quantity")
    return dict(stockpile_only_to_expanded_ratio=base/expanded,
                expanded_minus_stockpile_native=expanded-base,
                comparison_basis="issuer prospective same-product figures, conditional on commensurate stated basis",
                annual_output_estimate=None, china_free_service=None,
                Dy_Tb_split_identified=False, empirical_adaptation_effect_identified=False)
