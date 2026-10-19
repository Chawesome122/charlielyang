#!/usr/bin/env python3
"""Rebuild selected issued-rule clauses from hashed Federal Register originals.

This is a clause-level research extract, not a consolidated current-law engine.
No network, live EAR text, legal severity score or access estimate is used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from weaponized.semiconductors.provisions import check_clocks, normalize_text, verify_clause, issued_clause_phases, verify_technical_bounds

BOOK = ROOT / "codebooks/legal_provisions.json"
DEST = ROOT / "data/processed/legal_provisions"
DIAG = ROOT / "outputs/diagnostics/legal_provisions_validation.json"


def source_record(source_id):
    records = pd.read_csv(ROOT / "metadata/semiconductor_sources.csv").fillna("")
    selected = records.loc[records.source_id.eq(source_id) & records.status.eq("retrieved")]
    if selected.empty:
        raise ValueError(f"Missing archived source: {source_id}")
    record = selected.iloc[-1].to_dict()
    payload = (ROOT / record["path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != record["sha256"]:
        raise ValueError(f"Original source hash mismatch: {source_id}")
    return record, payload


def instruction_at(payload, xpath):
    """Return the preceding numbered AMDPAR in original document order."""
    root = ET.fromstring(payload)
    target = root.find(xpath)
    current = None
    for element in root.iter():
        if element is target:
            return current
        if element.tag == "AMDPAR":
            match = re.match(r"(\d+)\.", normalize_text(element))
            if match:
                current = int(match.group(1))
    raise ValueError("No operative clause located")


def build():
    book = json.loads(BOOK.read_text())
    documents = {}
    for spec in book["documents"]:
        text_source, payload = source_record(spec["source_id"])
        metadata_source, meta_payload = source_record(spec["metadata_source_id"])
        if text_source["sha256"] != spec["source_sha256"] or metadata_source["sha256"] != spec["metadata_sha256"]:
            raise ValueError("Source differs from the original bytes reviewed in the codebook")
        meta = json.loads(meta_payload)
        if meta["document_number"] != spec["document_number"]:
            raise ValueError("Original metadata document identity mismatch")
        if meta["publication_date"] != text_source["publication_date"]:
            raise ValueError("Original and metadata publication clocks disagree")
        verify_clause(payload, spec["document_number"], spec["dates_xpath"], spec["dates_quote"])
        if meta["publication_date"] > book["freeze"]:
            raise ValueError("Post-freeze issued original")
        documents[spec["document_number"]] = (spec, text_source, payload, metadata_source, meta)

    provisions, quotes, thresholds = [], [], []
    seen = set()
    for coded in book["clauses"]:
        if coded["claim_id"] in seen:
            raise ValueError("Duplicate immutable provision claim ID")
        seen.add(coded["claim_id"])
        spec, source, payload, metadata_source, meta = documents[coded["document_number"]]
        if coded["source_id"] != source["source_id"]:
            raise ValueError("Clause/source document mismatch")
        if coded["effective_date"] != meta["effective_on"]:
            raise ValueError("Selected clause must use its supported rule effect date")
        clocks = check_clocks(meta["publication_date"], coded["effective_date"], coded["compliance_date"], book["freeze"])
        # Validate the exact operative instruction against the preamble timing list.
        # Only this small original-rule chain is coded, never a generic legal parse.
        if coded["document_number"] == "2024-28270":
            delayed = {4, 5, 15, 16, 17, 19, 20, 21, 23, 25, 29, 31}
            expected = "2024-12-31" if coded["amendatory_instruction"] in delayed else "2024-12-02"
            if coded["compliance_date"] != expected:
                raise ValueError("Instruction-level compliance-date mismatch")
        elif coded["compliance_date"] != coded["effective_date"]:
            raise ValueError("Unsupported delayed compliance in selected clause")
        for index, evidence in enumerate(coded["evidence"], 1):
            quote = verify_clause(payload, coded["document_number"], evidence["xpath"], evidence["quote"])
            if instruction_at(payload, evidence["xpath"]) != coded["amendatory_instruction"]:
                raise ValueError(f"Operative instruction mismatch: {coded['claim_id']}")
            quotes.append(dict(claim_id=coded["claim_id"], evidence_sequence=index,
                              source_id=source["source_id"], source_sha256=source["sha256"],
                              source_path=source["path"], xpath=evidence["xpath"],
                              xml_tag=evidence["xml_tag"], quote=quote,
                              quote_sha256=hashlib.sha256(quote.encode()).hexdigest()))
        joined = " ".join(x["quote"] for x in coded["evidence"])
        verify_technical_bounds(joined, coded["parameter_bounds"])
        for index, bound in enumerate(coded["parameter_bounds"], 1):
            thresholds.append(dict(claim_id=coded["claim_id"], bound_sequence=index,
                                   source_id=source["source_id"], source_sha256=source["sha256"],
                                   document_number=coded["document_number"], legal_locator=coded["legal_locator"],
                                   conjunction="all_bounds_within_this_branch", **bound,
                                   legal_eligibility_determined=False, access_score_available=False))
        row = {k: v for k, v in coded.items() if k not in {"evidence", "parameter_bounds"}}
        row.update(publication_date=meta["publication_date"], info_public_date=meta["publication_date"],
                   earliest_public_date=None, source_sha256=source["sha256"], source_path=source["path"],
                   source_url=source["url"], retrieval_timestamp=source["retrieval_timestamp"],
                   metadata_source_id=metadata_source["source_id"], metadata_sha256=metadata_source["sha256"],
                   metadata_path=metadata_source["path"], original_citation=meta["citation"],
                   paragraph_count=len(coded["evidence"]), evidence_verified=True,
                   current_law_consolidation_certified=False, **clocks)
        provisions.append(row)

    by_id = {row["claim_id"]: row for row in book["clauses"]}
    links = []
    for row in book["clauses"]:
        previous = row.get("relates_to_claim_id")
        if previous:
            before = by_id[previous]
            unchanged = row["parameter_bounds"] == before["parameter_bounds"]
            if not unchanged:
                raise ValueError("Claimed restated technical parameters differ")
            links.append(dict(from_claim_id=previous, to_claim_id=row["claim_id"], relation=row["relation"],
                              selected_parameter_bounds_identical=True, complete_scope_unchanged_certified=False,
                              supersedes_full_instrument=False))
    DEST.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(provisions).to_csv(DEST / "provisions.csv", index=False)
    pd.DataFrame(quotes).to_csv(DEST / "quoted_elements.csv", index=False)
    pd.DataFrame(thresholds).to_csv(DEST / "technical_bounds.csv", index=False)
    pd.DataFrame(links).to_csv(DEST / "amendment_links.csv", index=False)
    phase_rows = []
    for origin in ["2023-10-24", "2023-10-25", "2023-11-17", "2024-12-03", "2024-12-05", "2024-12-30", "2024-12-31", "2026-01-15", book["freeze"]]:
        phase_rows.extend(dict(as_of=origin, **row) for row in issued_clause_phases(provisions, origin))
    pd.DataFrame(phase_rows).to_csv(DEST / "issued_phase_checks.csv", index=False)
    diagnostic = dict(passed=True, freeze=book["freeze"], empirical_class="primary_legal_text_descriptive_extract",
                      original_documents=len(documents), source_artifacts=2 * len(documents),
                      selected_provision_claims=len(provisions), exact_quoted_elements=len(quotes),
                      exact_dates_elements=len(documents), structured_technical_bounds=len(thresholds),
                      verified_parameter_restatement_links=len(links),
                      public_clock_basis="conservative_FR_publication; earlier_inspection_not_certified",
                      original_at_publication_byte_vintage_certified=False,
                      current_law_consolidation_certified=False, numerical_access_effect_estimated=False,
                      severity_score_assigned=False, observed_license_approvals=0,
                      independent_legal_or_second_coder_review=False,
                      gaps=["complete amendment, rescission, enforcement and country-group consolidation to freeze",
                            "intervening April2024, January2025 and later amendments beyond selected exact clauses",
                            "all underlying part734 jurisdiction/FDP and parts744/746 end-use/end-user conditions",
                            "complete NAC/ACA, TGL, related software/technology and Entity List transactions",
                            "first-public-inspection/source-at-vintage certification",
                            "transaction-level licenses, usable shipments, installed tools and technical target evidence",
                            "qualified independent legal review and blinded second coding"],
                      outputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.glob("*.csv"))})
    DIAG.parent.mkdir(parents=True, exist_ok=True)
    DIAG.write_text(json.dumps(diagnostic, indent=2) + "\n")
    print(json.dumps(diagnostic, indent=2))
    return diagnostic


if __name__ == "__main__":
    build()
