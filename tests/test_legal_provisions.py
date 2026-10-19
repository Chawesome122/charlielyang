"""Original-clause checks plus explicitly hypothetical boundary inputs.

Parameter screens never decide legal authorization or actual foreign access.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.semiconductors.provisions import (
    check_clocks, issued_clause_phases, parameter_screen, verify_clause,
)

ROOT = Path(__file__).resolve().parents[1]
BOOK = json.loads((ROOT / "codebooks/legal_provisions.json").read_text())
CLAUSES = {row["claim_id"]: row for row in BOOK["clauses"]}


def bounds(claim_id):
    return CLAUSES[claim_id]["parameter_bounds"]


def payload(document="2024-28270"):
    return next((ROOT / "data/raw/semiconductors").glob(f"SC-FR-{document}-TEXT-*.xml")).read_bytes()


def test_all_coded_paragraphs_match_exact_original_xml_and_document_identity():
    for claim in BOOK["clauses"]:
        original = payload(claim["document_number"])
        for evidence in claim["evidence"]:
            assert verify_clause(original, claim["document_number"], evidence["xpath"], evidence["quote"]) == evidence["quote"]
    example = CLAUSES["LP-2024-hbm-threshold"]["evidence"][0]
    with pytest.raises(ValueError, match="identity"):
        verify_clause(payload(), "2026-00789", example["xpath"], example["quote"])


def test_wrong_clause_locator_or_changed_quote_is_rejected():
    example = CLAUSES["LP-2024-hbm-threshold"]["evidence"][0]
    with pytest.raises(ValueError, match="exactly one"):
        verify_clause(payload(), "2024-28270", "./MISSING", example["quote"])
    with pytest.raises(ValueError, match="text mismatch"):
        verify_clause(payload(), "2024-28270", example["xpath"], example["quote"].replace("greater than 2", "greater than or equal to 2"))


def test_later_publication_is_allowed_but_never_backdated():
    result = check_clocks("2024-12-05", "2024-12-02", "2024-12-31")
    assert result["publication_after_effective"]
    assert not result["first_public_date_certified"]
    with pytest.raises(ValueError, match="Post-freeze"):
        check_clocks("2026-10-12", "2026-10-12", "2026-10-12")
    with pytest.raises(ValueError, match="Compliance"):
        check_clocks("2024-12-05", "2024-12-02", "2024-12-01")


def test_original_issue_phases_respect_publication_and_instruction_compliance():
    records = pd.read_csv(ROOT / "data/processed/legal_provisions/provisions.csv").to_dict("records")
    early = issued_clause_phases(records, "2024-12-03")
    assert not any(r["document_number"] == "2024-28270" for r in early)
    december = {r["claim_id"]: r for r in issued_clause_phases(records, "2024-12-05")}
    assert december["LP-2024-hbm-license"]["issued_phase"] == "effective_compliance_deferred"
    assert december["LP-2024-hbm-exception-threshold"]["issued_phase"] == "issued_compliance_date_reached_not_current_law_certified"
    assert "LP-2023-a1" in december  # no inferred complete supersession
    assert "LP-2024-a1" in december
    assert not issued_clause_phases(records, "2023-10-24")
    october = issued_clause_phases(records, "2023-10-25")
    assert {r["issued_phase"] for r in october} == {"announced_not_effective"}


@pytest.mark.parametrize("density, classified, exception", [
    (2, False, True), (2.00001, True, True), (3.29999, True, True), (3.3, True, False),
])
def test_hypothetical_hbm_strict_boundaries_are_distinct(density, classified, exception):
    # Hypothetical technical inputs; neither screen checks all item or route scope.
    variables = {"memory_bandwidth_density": density}
    assert parameter_screen(variables, bounds("LP-2024-hbm-threshold"))["parameter_bounds_satisfied"] is classified
    result = parameter_screen(variables, bounds("LP-2024-hbm-exception-threshold"))
    assert result["parameter_bounds_satisfied"] is exception
    assert not result["legal_eligibility_determined"]
    assert not result["license_approval_determined"]
    assert result["access_or_capability_score"] is None


def test_hypothetical_compute_review_requires_both_strict_bounds():
    gate = bounds("LP-2026-review")
    assert parameter_screen({"total_processing_performance": 20999, "total_dram_bandwidth": 6499}, gate)["parameter_bounds_satisfied"]
    assert not parameter_screen({"total_processing_performance": 21000, "total_dram_bandwidth": 6499}, gate)["parameter_bounds_satisfied"]
    assert not parameter_screen({"total_processing_performance": 20999, "total_dram_bandwidth": 6500}, gate)["parameter_bounds_satisfied"]
    assert parameter_screen({"total_processing_performance": 20999}, gate)["parameter_bounds_satisfied"] is None
    assert parameter_screen({"total_processing_performance": 21000}, gate)["parameter_bounds_satisfied"] is False


def test_hypothetical_compute_branch_inclusive_and_exclusive_endpoints():
    # The four branches are alternatives, and qualifying technical parameters are
    # still subject to notes, jurisdiction, destination, end-user and authorization.
    assert parameter_screen({"total_processing_performance": 4800}, bounds("LP-2023-a1"))["parameter_bounds_satisfied"]
    assert parameter_screen({"total_processing_performance": 1600, "performance_density": 5.92}, bounds("LP-2023-a2"))["parameter_bounds_satisfied"]
    assert parameter_screen({"total_processing_performance": 2400, "performance_density": 1.6}, bounds("LP-2023-b1"))["parameter_bounds_satisfied"]
    assert not parameter_screen({"total_processing_performance": 4800, "performance_density": 1.6}, bounds("LP-2023-b1"))["parameter_bounds_satisfied"]
    assert not parameter_screen({"total_processing_performance": 2400, "performance_density": 5.92}, bounds("LP-2023-b1"))["parameter_bounds_satisfied"]
    assert parameter_screen({"total_processing_performance": 1600, "performance_density": 3.2}, bounds("LP-2023-b2"))["parameter_bounds_satisfied"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1])
def test_missing_is_explicit_and_invalid_technical_input_rejected(bad):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        parameter_screen({"memory_bandwidth_density": bad}, bounds("LP-2024-hbm-threshold"))
    assert parameter_screen({}, bounds("LP-2024-hbm-threshold"))["parameter_bounds_satisfied"] is None


def test_unregistered_operator_and_empty_bounds_fail():
    with pytest.raises(ValueError, match="operator"):
        parameter_screen({"x": 2}, [{"variable": "x", "operator": "~", "value": 2}])
    with pytest.raises(ValueError, match="needs quoted bounds"):
        parameter_screen({}, [])


def test_all_nine_certification_conditions_and_testing_are_retained():
    expected = {"US-shipments", "US-supply", "50-percent", "enduses", "KYC", "remote-users", "IaaS", "security", "every-shipment"}
    assert all("LP-2026-" + name in CLAUSES for name in expected)
    assert len(CLAUSES["LP-2026-IaaS"]["evidence"]) == 4
    assert len(CLAUSES["LP-2026-independent-lab"]["evidence"]) == 4
    assert len(CLAUSES["LP-2026-DRAM-definition"]["evidence"]) == 3
    assert CLAUSES["LP-2026-review"]["license_coding"] == "conditional_case_by_case_license_review_not_approval"


def test_restatement_links_are_parameter_only_and_do_not_erase_originals():
    links = pd.read_csv(ROOT / "data/processed/legal_provisions/amendment_links.csv")
    assert len(links) == 4
    assert links.selected_parameter_bounds_identical.all()
    assert not links.complete_scope_unchanged_certified.any()
    assert not links.supersedes_full_instrument.any()
    for row in links.to_dict("records"):
        assert bounds(row["from_claim_id"]) == bounds(row["to_claim_id"])


def test_processed_sources_and_quotes_have_live_original_hashes():
    frame = pd.read_csv(ROOT / "data/processed/legal_provisions/provisions.csv")
    assert not frame.current_law_consolidation_certified.any()
    assert not frame.approval_observed.any()
    assert frame.severity_ordinal.isna().all()
    assert frame.physical_access_loss.isna().all()
    for row in frame[["source_path", "source_sha256", "metadata_path", "metadata_sha256"]].drop_duplicates().to_dict("records"):
        assert hashlib.sha256((ROOT / row["source_path"]).read_bytes()).hexdigest() == row["source_sha256"]
        assert hashlib.sha256((ROOT / row["metadata_path"]).read_bytes()).hexdigest() == row["metadata_sha256"]
    quotes = pd.read_csv(ROOT / "data/processed/legal_provisions/quoted_elements.csv")
    assert not quotes.duplicated(["claim_id", "evidence_sequence"]).any()
    assert quotes.apply(lambda r: hashlib.sha256(r["quote"].encode()).hexdigest() == r["quote_sha256"], axis=1).all()


@pytest.mark.parametrize("mutation", ["swap_variables", "swap_values", "swap_units"])
def test_builder_rejects_nearby_parameter_recoding_before_writing_outputs(tmp_path, monkeypatch, mutation):
    """All original numbers/signs remain present, but their association is false."""
    import copy
    import runpy
    module = runpy.run_path(str(ROOT / "scripts/build_legal_provisions.py"))
    changed = copy.deepcopy(BOOK)
    claim = next(c for c in changed["clauses"] if c["claim_id"] == "LP-2026-review")
    left, right = claim["parameter_bounds"]
    if mutation == "swap_variables":
        left["variable"], right["variable"] = right["variable"], left["variable"]
        # Keep each recoded variable's unit coherent to expose the semantic
        # association error rather than merely triggering the unit guard.
        left["native_unit"], right["native_unit"] = right["native_unit"], left["native_unit"]
    elif mutation == "swap_values":
        left["value"], right["value"] = right["value"], left["value"]
    else:
        left["native_unit"], right["native_unit"] = right["native_unit"], left["native_unit"]
    book_path = tmp_path / "mutated_codebook.json"
    book_path.write_text(json.dumps(changed))
    destination = tmp_path / "derived"
    builder = module["build"]
    monkeypatch.setitem(builder.__globals__, "BOOK", book_path)
    monkeypatch.setitem(builder.__globals__, "DEST", destination)
    monkeypatch.setitem(builder.__globals__, "DIAG", tmp_path / "diagnostics.json")
    with pytest.raises(ValueError, match="Technical bound"):
        builder()
    assert not destination.exists()
    assert not (tmp_path / "diagnostics.json").exists()
