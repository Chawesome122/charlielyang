"""ASX-vintaged native Korean Metals Plant measurements."""

from datetime import date, timedelta
from decimal import Decimal
import re

from weaponized.io.original_text import normalize_evidence, verified_original_text
from weaponized.rare_earths.followup import FREEZE, extract_claims, source_clocks


def load_shipments(root, specs, sources):
    clocks = source_clocks(root, sources)
    for sid, source in sources.items():
        period = date.fromisoformat(source["report_period_end"])
        original = verified_original_text(root / source["archive_path"], source["sha256"])
        date_phrase = f"{period.day} {period:%B %Y}"
        page = normalize_evidence(original.split("\f")[0])
        if f"Quarterly Activities Report to {date_phrase}" not in page:
            raise ValueError(f"Quarterly report period mismatch: {sid}")
        clocks[sid]["report_period_end"] = period.isoformat()
    claims, tokens = extract_claims(root, specs, sources, clocks, preserve_native_tokens=True)
    for claim in claims:
        token = tokens[claim["claim_id"]].get("value")
        unit = claim["native_unit"]
        if token is None and unit is not None:
            raise ValueError(f"Native unit lacks a quantity: {claim['claim_id']}")
        if token is not None and (
            unit not in {"tonnes", "kg"} or re.fullmatch(r"~?\d+(?:\.\d+)?", token) is None
        ):
            raise ValueError(f"Invalid native quantity token: {claim['claim_id']}")
        if claim["evidence_role"] in {"observed_dispatch", "observed_production"}:
            end = date.fromisoformat(claim["report_period_end"])
            if claim["comparative"]:
                end = end.replace(month=end.month - 2, day=1) - timedelta(days=1)
                if claim["evidence_role"] != "observed_dispatch":
                    raise ValueError(f"Invalid comparative role: {claim['claim_id']}")
            start = end.replace(month=end.month - 2, day=1)
            if (claim["event_date_lower"], claim["event_date_upper"]) != (start.isoformat(), end.isoformat()):
                raise ValueError(f"Invalid dispatch or production period: {claim['claim_id']}")
        claim.update(
            native_quantity_token=token,
            native_quantity=Decimal(token.lstrip("~")) if token else None,
            source_marks_approximate=bool(token and (
                token.startswith("~") or re.search(rf"\bapproximately {re.escape(token)}\b", claim["quote"])
            )),
        )
    return claims, clocks


def visible_plant_dispatches(claims, origin):
    """Select one issuer vintage per period and product for plant dispatch totals."""
    if origin > FREEZE:
        raise ValueError("Information cutoff exceeded")
    candidates = {}
    cutoff = origin.isoformat()
    for row in claims:
        if (
            row["evidence_role"] != "observed_dispatch" or row["info_public_date"] > cutoff
            or row["event_date_upper"] > cutoff
        ):
            continue
        key = row["event_date_upper"], row["product_form"]
        prior = candidates.get(key)
        if prior and prior["info_public_date"] == row["info_public_date"]:
            raise ValueError(f"Ambiguous same-day dispatch versions: {key}")
        if prior is None or row["info_public_date"] > prior["info_public_date"]:
            candidates[key] = row
    return candidates


def difference(left, right, *, reason):
    """Subtract matched native reports and retain their scope and source evidence."""
    compatible = {
        "within_quarter_production_minus_dispatch": (
            left["event_date_upper"] == right["event_date_upper"]
            and left["evidence_role"] == "observed_production" and right["evidence_role"] == "observed_dispatch"
        ),
        "quarter_over_quarter_dispatch_change": (
            left["event_date_upper"] > right["event_date_upper"]
            and left["evidence_role"] == right["evidence_role"] == "observed_dispatch"
        ),
    }
    if (
        not compatible.get(reason) or left["product_form"] != right["product_form"]
        or left["native_unit"] != right["native_unit"] or left["counterparty_or_scope"] != "KMP"
        or right["counterparty_or_scope"] != "KMP"
    ):
        raise ValueError("Incompatible period, scope, material or measurement role")
    return dict(
        comparison=reason, left_claim=left["claim_id"], right_claim=right["claim_id"],
        product_form=left["product_form"], native_unit=left["native_unit"],
        left_native=left["native_quantity"], right_native=right["native_quantity"],
        difference_native=left["native_quantity"] - right["native_quantity"],
        stock_delta_identified=False, measured_element_flow_identified=False,
    )
