"""Forecast availability and identification gates, not fabricated effects."""

from __future__ import annotations

import pandas as pd


def forecast_availability(origin, horizon_months, outcome_public_date, target_version, outcome_target_version, *, freeze="2026-10-11"):
    origin = pd.Timestamp(origin)
    endpoint = origin + pd.DateOffset(months=horizon_months)
    if horizon_months not in [6, 12, 24]:
        raise ValueError("Registered semiconductor forecast horizons are 6,12,24 months")
    # Blueprint endpoints are calendar-end based (Dec 31 +6m = June 30).
    if origin.is_month_end:
        endpoint = endpoint + pd.offsets.MonthEnd(0)
    freeze = pd.Timestamp(freeze)
    public = pd.to_datetime(outcome_public_date, errors="raise") if pd.notna(outcome_public_date) else pd.NaT
    reasons = []
    if origin > freeze:
        reasons.append("origin_after_freeze")
    if endpoint > freeze:
        reasons.append("endpoint_unobserved_at_freeze")
    if pd.isna(public):
        reasons.append("outcome_public_date_unknown")
    elif public > freeze:
        reasons.append("outcome_not_public_at_freeze")
    elif public < endpoint:
        reasons.append("outcome_release_before_endpoint_verify_measurement_window")
    if target_version != outcome_target_version:
        reasons.append("target_version_mismatch")
    return {"origin": str(origin.date()), "endpoint": str(endpoint.date()), "eligible": not reasons, "reasons": reasons}


def identification_feasibility(panel: pd.DataFrame, *, parallel_trends_justified=False, spillovers_addressed=False):
    """Fail closed before any group-time ATT claim.

    No automated gate can establish parallel trends. The two arguments require
    an evidence memo; they are not estimated from an insignificant pretrend.
    """
    required = {"firm_id", "parent_id", "period", "outcome", "first_treatment", "exposure_base_year", "technology_risk_set", "info_public_date"}
    reasons = []
    if panel.empty:
        reasons.append("no_observed_firm_product_panel")
    if not required.issubset(panel.columns):
        reasons.append("required_panel_fields_missing")
    else:
        if panel[list(required - {"first_treatment"})].isna().any().any():
            reasons.append("required_observations_missing")
        if (panel.exposure_base_year > 2021).any():
            reasons.append("post_policy_exposure_weights")
        if panel.parent_id.nunique() < 2:
            reasons.append("insufficient_independent_clusters")
        if panel.first_treatment.notna().all():
            reasons.append("control_risk_set_requires_overlap_and_not_yet_treated_check")
    if not parallel_trends_justified:
        reasons.append("conditional_parallel_trends_unjustified")
    if not spillovers_addressed:
        reasons.append("policy_spillovers_unresolved")
    return {"causal_estimation_permitted": not reasons, "reasons": reasons,
            "estimand_if_identified": "cohort-time ATT(g,t), publication and effective event clocks separate"}
