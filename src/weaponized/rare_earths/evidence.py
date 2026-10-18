"""Documentation coverage within a selected project roster, not supply estimates."""
import math
import re

import pandas as pd


def capacity_time_basis(value, native_unit):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "missing"
    if not math.isfinite(amount) or amount <= 0:
        return "missing"
    unit = str(native_unit or "")
    # A real disclosure says TOTAL demonstration campaign, NOT per year. The
    # positive annual-unit substring must not override that explicit qualifier.
    if (re.search(r"\b(total|finite)\b", unit, re.I) and re.search(r"\b(campaign|batch)\b", unit, re.I)) or re.search(r"(?:per |/)(campaign|batch)\b", unit, re.I):
        return "finite_batch_or_campaign_total"
    if re.search(r"not per year|temporal basis not explicit", unit, re.I):
        return "unknown_time_basis"
    if re.search(r"/(year|yr)|per (year|annum)|\b(mtpa|tpa)\b", unit, re.I):
        return "annual_native_capacity"
    return "unknown_time_basis"


def documented_activity_snapshot(frame, freeze="2026-10-11"):
    """Select source-visible snapshots and expose missing coverage explicitly.

    Undated candidates remain in the discovery denominator but are ineligible
    for as-of estimates. Future published versions are excluded entirely.
    """
    data = frame.copy()
    dates = pd.to_datetime(data.info_public_date, errors="coerce")
    cutoff = pd.Timestamp(freeze)
    data = data[dates.isna() | dates.le(cutoff)].copy()
    data["public_clock_eligible"] = pd.to_datetime(data.info_public_date, errors="coerce").le(cutoff)
    data = data.sort_values(["info_public_date", "valid_date", "record_id"], na_position="first")
    data = data.drop_duplicates("activity_id", keep="last").copy()
    data["capacity_time_basis"] = [capacity_time_basis(r.capacity_native, r.native_unit) for r in data.itertuples()]
    data["native_capacity_documented"] = data.capacity_time_basis.ne("missing")
    data["annual_native_capacity_documented"] = data.capacity_time_basis.eq("annual_native_capacity")
    data["finite_campaign_limit_documented"] = data.capacity_time_basis.eq("finite_batch_or_campaign_total")
    # These fields count independently verified records, not actual industrial
    # absence. No documented recipe/route/demand evidence is inferred from prose.
    for field in ["complete_element_recipe_verified", "finite_route_capacity_verified",
                  "independent_stable_qualified_rate_verified", "final_grade_demand_matched"]:
        data[field] = data[field].eq(True) if field in data else False
    return data
