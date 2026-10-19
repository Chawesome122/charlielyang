"""Native plant disclosures: diagnostic ratios and inventory admission gates.

No operation converts generic tons, oxalate, carbonate or work in process into
qualified oxide supply. Dates and product identities remain separate evidence.
"""
from datetime import date
import math


def reported_flow_ratio(feed, output, feed_unit, output_unit):
    if not all(math.isfinite(x) and x >= 0 for x in [feed, output]) or feed == 0:
        raise ValueError("Finite positive processed feed and nonnegative output required")
    matched_units = feed_unit == output_unit == "metric_tonnes"
    return dict(reported_product_per_bulk_feed=output/feed if matched_units else None,
                missing_reason=None if matched_units else "native ton standard not established; no exact conversion inferred from rounded glossary",
                chemical_recovery=None, plant_utilization=None, China_free_service=None,
                precision_basis="Arithmetic of reported rounded/approximate quantities, not measurement precision or a confidence interval",
                interpretation="Same-episode native product/feed comparison only; product form, assay, inventory and process balance remain separate")


def opening_stock_readiness(row, origin, *, stock_bridge_verified=False, physical_form_verified=False):
    """Gate finished/separated opening stock; WIP needs a different commodity ledger."""
    cut = date.fromisoformat(origin)
    if cut > date(2026, 10, 11):
        raise ValueError("Research information freeze exceeded")
    public = date.fromisoformat(row["info_public_date"]) <= cut
    measured = row["measurement_date_known"]
    if not all(isinstance(flag, bool) for flag in [measured, stock_bridge_verified, physical_form_verified]):
        raise ValueError("Stock evidence flags must be explicit booleans")
    quantity = float(row["value"])
    if not math.isfinite(quantity) or quantity < 0:
        raise ValueError("Stock quantity must be finite and nonnegative")
    snapshot = date.fromisoformat(row["valid_date"])
    dated = measured and snapshot <= cut
    bridged = dated and (snapshot == cut or stock_bridge_verified)
    final_product = row["quantity_role"] == "separated_product_inventory"
    eligible = public and bridged and final_product and physical_form_verified
    return dict(source_public_at_origin=public, measurement_date_explicit=measured,
                measurement_at_or_before_origin=dated, dated_stock_bridge_available=bridged,
                final_separated_product_candidate=final_product,
                physical_form_verified=physical_form_verified,
                opening_stock_admissible=eligible,
                usable_opening_stock_value=quantity if eligible else None,
                missing_stock_is_not_zero=True,
                no_sales_or_work_in_process_added_to_finished_stock=True)


def capacity_identity(first_phase, second_phase, reported_combined):
    values = [first_phase, second_phase, reported_combined]
    if not all(math.isfinite(x) and x >= 0 for x in values):
        raise ValueError("Finite nonnegative same-product table values required")
    residual = first_phase+second_phase-reported_combined
    return dict(component_sum=first_phase+second_phase, reported_combined=reported_combined,
                residual=residual, passed=abs(residual) <= 1e-9,
                combined_must_not_be_added_again=True,
                verified_table_arithmetic_only=True, observed_operating_capacity_verified=False)


def reported_form_set(rows, origin):
    cutoff = date.fromisoformat(origin)
    if cutoff > date(2026, 10, 11):
        raise ValueError("Research information freeze exceeded")
    visible = [r for r in rows if date.fromisoformat(r["info_public_date"]) <= cutoff]
    forms = sorted({r["product_basis"] for r in visible})
    status = ("not_yet_public" if not forms else
              "one_reported_form_not_independently_verified" if len(forms) == 1 else
              "different_reported_forms_require_adjudication")
    return dict(origin=origin, visible_versions=len(visible), forms=";".join(forms),
                status=status, mass_conversion_authorized=False,
                later_wording_silently_overwrites_earlier=False,
                physical_oxide_equivalent_identified=False)
