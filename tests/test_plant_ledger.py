"""Physical bases, dated stocks and conditional plans must not be conflated."""
import json
from pathlib import Path
import re
import runpy

import pandas as pd
import pytest

from weaponized.io.original_text import verified_original_text, normalize_evidence
from weaponized.rare_earths.plant_ledger import capacity_identity, opening_stock_readiness, reported_flow_ratio, reported_form_set

ROOT = Path(__file__).resolve().parents[1]


def stock(**updates):
    row = dict(info_public_date="2026-02-26", valid_date="2025-12-31", value=34.,
               measurement_date_known=True, quantity_role="separated_product_inventory")
    return row | updates


def test_source_reported_ratio_does_not_estimate_chemical_recovery():
    result = reported_flow_ratio(500, 38, "metric_tonnes", "metric_tonnes")
    assert result["reported_product_per_bulk_feed"] == pytest.approx(.076)
    assert result["chemical_recovery"] is None and result["plant_utilization"] is None
    assert reported_flow_ratio(1, 2, "metric_tonnes", "metric_tonnes")["reported_product_per_bulk_feed"] == 2


def test_generic_tons_are_not_silently_converted_to_metric_tonnes():
    result = reported_flow_ratio(400, 120, "native_tons_unspecified", "metric_tonnes")
    assert result["reported_product_per_bulk_feed"] is None
    assert "rounded glossary" in result["missing_reason"]


@pytest.mark.parametrize("feed,out", [(0, 38), (-1, 38), (500, -1), (float("nan"), 38), (500, float("inf"))])
def test_invalid_flow_quantities_rejected(feed, out):
    with pytest.raises(ValueError):
        reported_flow_ratio(feed, out, "metric_tonnes", "metric_tonnes")


def test_year_end_stock_cannot_leak_before_publication_or_carry_forward_without_bridge():
    before = opening_stock_readiness(stock(), "2025-12-31", physical_form_verified=True)
    assert not before["source_public_at_origin"] and before["usable_opening_stock_value"] is None
    known = opening_stock_readiness(stock(), "2026-02-26", physical_form_verified=True)
    assert known["source_public_at_origin"] and not known["dated_stock_bridge_available"]
    assert not known["opening_stock_admissible"]
    assert opening_stock_readiness(stock(), "2026-02-26", stock_bridge_verified=True, physical_form_verified=True)["usable_opening_stock_value"] == 34


def test_missing_measurement_date_and_work_in_process_do_not_become_finished_stock():
    unknown = opening_stock_readiness(stock(measurement_date_known=False), "2026-02-26", stock_bridge_verified=True, physical_form_verified=True)
    assert not unknown["opening_stock_admissible"]
    wip = opening_stock_readiness(stock(quantity_role="work_in_process"), "2026-02-26", stock_bridge_verified=True, physical_form_verified=True)
    assert not wip["final_separated_product_candidate"] and wip["usable_opening_stock_value"] is None


def test_form_verification_is_separate_from_dated_stock_bridge():
    result = opening_stock_readiness(stock(), "2026-02-26", stock_bridge_verified=True)
    assert result["dated_stock_bridge_available"] and not result["physical_form_verified"]
    assert result["usable_opening_stock_value"] is None


@pytest.mark.parametrize("update", [{"measurement_date_known":"False"}, {"value":-1}, {"value":float("nan")}])
def test_invalid_stock_evidence_rejected(update):
    with pytest.raises(ValueError):
        opening_stock_readiness(stock(**update), "2026-02-26")


def test_freeze_rejects_post_cutoff_origins():
    with pytest.raises(ValueError):
        opening_stock_readiness(stock(), "2026-10-12")
    with pytest.raises(ValueError):
        reported_form_set([], "2026-10-12")


def test_table_combined_capacity_cannot_be_added_to_its_components():
    assert capacity_identity(1049, 5513, 6562)["passed"]
    assert capacity_identity(12, 48, 60)["passed"]
    assert capacity_identity(35, 165, 200)["passed"]
    assert not capacity_identity(1049+6562, 5513, 6562)["passed"]
    assert not capacity_identity(1049, 5513, 6562)["observed_operating_capacity_verified"]


def test_later_oxide_wording_does_not_erase_earlier_oxalate_description():
    rows = [dict(info_public_date="2025-02-26",product_basis="NdPr_oxalate"),
            dict(info_public_date="2026-02-26",product_basis="NdPr_oxide")]
    assert reported_form_set(rows, "2024-12-31")["status"] == "not_yet_public"
    early = reported_form_set(rows, "2025-03-31")
    assert early["visible_versions"] == 1 and early["forms"] == "NdPr_oxalate"
    late = reported_form_set(rows, "2026-10-11")
    assert late["status"] == "different_reported_forms_require_adjudication"
    assert not late["mass_conversion_authorized"]


def test_originals_support_form_difference_and_finished_stock_is_explicitly_dated():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    table = pd.read_csv(ROOT/"data/processed/white_mesa/observations.csv")
    for year, form in [(2024,"oxalate"), (2025,"oxide")]:
        source = sources[f"RE-EF-10K{year}"]
        text = normalize_evidence(verified_original_text(ROOT/source["archive_path"],source["sha256"]))
        assert f"by processing 500 tonnes of monazite and producing 38 tonnes of NdPr {form}." in text
        selected = table[table.source_id.eq(f"RE-EF-10K{year}") & table.episode_id.eq("WhiteMesa_2024_commissioning_run") & table.variable.eq("reported_output")]
        assert len(selected) == 1 and selected.iloc[0].product_basis == f"NdPr_{form}"
        assert float(selected.iloc[0].value) == 38
        if year == 2025:
            assert "As of December 31, 2025, approximately 34 tonnes of separated NdPr remain in inventory." in text


def test_source_guard_rejects_oxide_assumption_and_silent_ton_conversion():
    guard = runpy.run_path(str(ROOT/"scripts/build_white_mesa.py"))["verify_mass_basis"]
    match = re.search(r"producing (?P<output>38) tonnes of NdPr oxalate", "producing 38 tonnes of NdPr oxalate")
    spec = dict(quantity_role="reported_production", numeric_group="output", native_unit="metric_tonnes", product_basis="NdPr_oxalate")
    guard(spec, match)
    with pytest.raises(ValueError, match="chemical/product"):
        guard(spec | {"product_basis":"NdPr_oxide"}, match)
    with pytest.raises(ValueError, match="native ton"):
        guard(spec | {"native_unit":"native_tons_unspecified"}, match)


def test_actual_ledger_preserves_basis_corrections_and_missing_opening_stock():
    table = pd.read_csv(ROOT/"data/processed/white_mesa/observations.csv")
    assert len(table) == 49 and table.record_version_id.is_unique
    audit = pd.read_csv(ROOT/"data/processed/white_mesa/stock_origin_audit.csv")
    assert len(audit) == 20 and not audit.opening_stock_admissible.any()
    assert audit.usable_opening_stock_value.isna().all()
    stocks = table[table.variable.eq("reported_stock")]
    assert len(stocks) == 5 and stocks.measurement_date_known.sum() == 1
    corrected = pd.read_csv(ROOT/"data/processed/white_mesa/basis_corrections.csv")
    assert len(corrected) == 3 and corrected.corrected_research_label.eq("separated_NdPr_reported_product_form_unconfirmed").all()
