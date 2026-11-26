from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest

from weaponized.rare_earths.kmp_shipments import difference, load_shipments, visible_plant_dispatches

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    sources = {row["source_id"]: row for row in json.loads(
        (ROOT / "metadata/kmp_shipments_sources.json").read_text()
    )}
    specs = json.loads((ROOT / "codebooks/kmp_shipments_claims.json").read_text())
    claims, _ = load_shipments(ROOT, specs, sources)
    return sources, specs, {row["claim_id"].removeprefix("KMP:"): row for row in claims}


def test_later_comparative_does_not_enter_earlier_origin(evidence):
    _, _, rows = evidence
    key = ("2026-03-31", "NdFeB_strip_alloy")
    before = visible_plant_dispatches(rows.values(), date(2026, 7, 29))
    after = visible_plant_dispatches(rows.values(), date(2026, 7, 30))
    assert before[key]["claim_id"] == "KMP:alloy_dispatch_q1_26"
    assert after[key]["claim_id"] == "KMP:alloy_dispatch_q1_comparative"
    assert ("2026-03-31", "Nd_and_NdPr_metal") not in before
    with pytest.raises(ValueError, match="cutoff"):
        visible_plant_dispatches(rows.values(), date(2026, 10, 12))


def test_comparative_cannot_be_reassigned_to_another_quarter(evidence):
    sources, specs, _ = evidence
    spec = next(r for r in specs if r["claim_id"] == "KMP:alloy_dispatch_q3_comparative")
    shifted = spec | {"event_date_lower": "2025-04-01", "event_date_upper": "2025-06-30"}
    with pytest.raises(ValueError, match="Invalid dispatch or production period"):
        load_shipments(ROOT, [shifted], sources)


def test_metal_and_alloy_are_incompatible_in_stock_diagnostic(evidence):
    _, _, rows = evidence
    reason = "within_quarter_production_minus_dispatch"
    result = difference(rows["metal_produced_q3_25"], rows["metal_dispatch_q3_25"], reason=reason)
    assert result["difference_native"] == Decimal("-20.5")
    assert result["stock_delta_identified"] is False
    with pytest.raises(ValueError, match="Incompatible"):
        difference(rows["metal_produced_q3_25"], rows["alloy_dispatch_q3_25"], reason=reason)


def test_order_and_customer_lots_do_not_become_plant_dispatches(evidence):
    _, _, rows = evidence
    result = visible_plant_dispatches(rows.values(), date(2025, 7, 23))
    assert result == {}
    dispatch, receipt = rows["vac_dispatch_q2_25"], rows["vac_receipt_q3_25"]
    assert dispatch["native_quantity"] == receipt["native_quantity"] == Decimal("1.2")
    assert (dispatch["event_date_upper"], receipt["event_date_lower"]) == ("2025-06-30", "2025-07-01")


def test_approximation_and_native_units_survive_extraction(evidence):
    _, _, rows = evidence
    assert rows["alloy_dispatch_q2_26"]["native_quantity_token"] == "~36"
    assert rows["alloy_dispatch_q4_25"]["source_marks_approximate"] is True
    assert rows["narva_tb_dispatch"]["native_unit"] == "kg"
    assert rows["narva_tb_dispatch"]["native_quantity"] == Decimal("2")
    assert rows["q1_feed_receipt"]["native_quantity"] is None
