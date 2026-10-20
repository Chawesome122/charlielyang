"""Rebuild complete party-entry schedules from nine pinned issued-rule originals."""
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

from weaponized.semiconductors.entity_schedules import parse_entity_schedule, visible_issued_entries, reported_filing_date, adjudicate_entry_actions
from weaponized.semiconductors.provisions import verify_clause, normalize_text

ROOT = Path(__file__).resolve().parents[1]


def build():
    book = json.loads((ROOT/"codebooks/entity_schedules.json").read_text())
    records = {r["source_id"]: r for r in map(json.loads, (ROOT/"metadata/legal_discovery_acquisitions.jsonl").read_text().splitlines()) if r["status"] == "downloaded"}
    screen = pd.read_csv(ROOT/"codebooks/legal_discovery_screening.csv")
    action_crosswalk=pd.read_csv(ROOT/"codebooks/entity_entry_actions.csv",keep_default_na=False)
    expected = set(screen.loc[screen.decision.eq("ENTITY_SCOPE_MAPPING_REQUIRED"), "document_number"])
    if {d["document_number"] for d in book["documents"]} != expected:
        raise ValueError("Entity-schedule selection differs from all nine pending original scope screens")
    entries, rows, notes, instructions, clocks, vintage_checks = [], [], [], [], [], []
    for spec in book["documents"]:
        source = records[spec["source_id"]]
        metadata = records[spec["metadata_source_id"]]
        payload = (ROOT/source["archive_path"]).read_bytes()
        meta_bytes = (ROOT/metadata["archive_path"]).read_bytes()
        if hashlib.sha256(meta_bytes).hexdigest() != spec["metadata_sha256"] or metadata["sha256"] != spec["metadata_sha256"] or source["sha256"] != spec["source_sha256"]:
            raise ValueError("Reviewed legal source/metadata checksum mismatch")
        meta = json.loads(meta_bytes)
        if any(meta[k] != spec[v] for k,v in [("document_number","document_number"),("publication_date","publication_date"),("effective_on","effective_date")]):
            raise ValueError("Issued metadata identity/clock differs from reviewed codebook")
        if spec["publication_date"] > book["freeze"] or spec["effective_date"] > book["freeze"]:
            raise ValueError("Post-freeze legal schedule")
        parsed = parse_entity_schedule(payload, spec)
        subset=action_crosswalk[action_crosswalk.source_id.eq(spec["source_id"])].to_dict("records")
        parsed["entries"]=adjudicate_entry_actions(payload,spec,parsed["entries"],subset)
        root = ET.fromstring(payload)
        trailer = normalize_text(root.find("./FRDOC"))
        filed = reported_filing_date(trailer, spec["document_number"])
        if filed != spec["reported_filing_date"] or filed > spec["publication_date"]:
            raise ValueError("Reviewed filing/publication clocks disagree")
        display = datetime.strptime(spec["effective_date"], "%Y-%m-%d").strftime("%B %-d, %Y")
        if display not in parsed["dates_quote"]:
            raise ValueError("Original effective-date passage does not support metadata clock")
        shared = dict(source_id=source["source_id"], source_sha256=source["sha256"], source_path=source["archive_path"],
                      source_url=source["url"], retrieval_timestamp=source["retrieval_timestamp"],
                      metadata_source_id=metadata["source_id"], metadata_sha256=metadata["sha256"],
                      publication_date=spec["publication_date"], info_public_date=filed,
                      effective_date=spec["effective_date"], original_citation=meta["citation"],
                      first_public_clock_basis="official original FRDOC reported filing date; day-end convention, globally earliest disclosure and release-time binaries not certified",
                      historical_source_byte_vintage_certified=False,
                      document_number=spec["document_number"])
        entries.extend(shared | e for e in parsed["entries"])
        for name, target in [("source_rows",rows),("table_notes",notes),("amendatory_instructions",instructions)]:
            for item in parsed[name]:
                verify_clause(payload, spec["document_number"], item["xpath"], item["quote"])
                target.append(shared | item)
        dates = dict(shared, xpath=parsed["dates_xpath"], quote=parsed["dates_quote"],
                     public_minus_effective_days=(date.fromisoformat(spec["publication_date"])-date.fromisoformat(spec["effective_date"])).days,
                     filing_minus_effective_days=(date.fromisoformat(filed)-date.fromisoformat(spec["effective_date"])).days,
                     filing_xpath="./FRDOC[1]", filing_quote=trailer,
                     globally_earliest_public_date=None)
        clocks.append(dates)
        frame = pd.DataFrame([shared | e for e in parsed["entries"]])
        before = str(date.fromisoformat(filed)-timedelta(days=1))
        at_effect = visible_issued_entries(frame, spec["effective_date"])
        at_public = visible_issued_entries(frame, spec["publication_date"])
        vintage_checks.append(dict(document_number=spec["document_number"],
                                   last_prefiling_origin=before,
                                   known_effective_entries_before_filing=len(visible_issued_entries(frame, before)),
                                   known_effective_entries_at_effective_date=len(at_effect),
                                   known_effective_entries_at_publication=len(at_public),
                                   publication_only_omits_at_effective_date=len(at_effect)-len(visible_issued_entries(frame,spec["effective_date"],clock="publication_date")),
                                   filing_precedes_effective_date=filed<spec["effective_date"],
                                   passed=len(visible_issued_entries(frame,before))==0 and len(at_public)==len(frame)))
    out = ROOT/"data/processed/entity_schedules"
    out.mkdir(parents=True, exist_ok=True)
    tables = dict(entries=entries, source_rows=rows, table_notes=notes,
                  amendatory_instructions=instructions, source_clocks=clocks,
                  publication_vintage_checks=vintage_checks)
    for name, data in tables.items():
        pd.DataFrame(data).to_csv(out/f"{name}.csv", index=False)
    frame = pd.DataFrame(entries)
    if frame.entry_id.duplicated().any():
        raise ValueError("Duplicate immutable schedule entry IDs")
    result = dict(passed=all(x["passed"] for x in vintage_checks), freeze=book["freeze"],
                  original_rules=len(book["documents"]), printed_entry_versions=len(entries),
                  original_table_rows=len(rows), table_notes=len(notes), amendatory_instructions=len(instructions),
                  source_clock_checks=len(clocks), vintage_checks=len(vintage_checks),
                  distinct_printed_destinations=frame.destination.nunique(),
                  review_categories=frame.review_category.value_counts().to_dict(),
                  printed_address_entries=int(frame.entry_kind.eq("address_entry").sum()),
                  unambiguously_added_entry_versions=int(frame.action_adjudication.eq("addition").sum()),
                  revised_entry_versions=int(frame.action_adjudication.eq("revision").sum()),
                  entry_action_crosswalk_records=len(action_crosswalk),
                  mixed_document_entry_actions_unresolved=int((~frame.action_adjudication.isin(["addition","revision"])).sum()),
                  source_row_counts={d["document_number"]:d["expected_table_rows"] for d in book["documents"]},
                  unique_new_firms_identified=False, complete_current_law_verified=False,
                  observed_license_outcomes=False, access_loss_or_capability_identified=False,
                  independent_legal_coding=False, original_at_vintage_bytes_certified=False)
    (ROOT/"outputs/diagnostics/entity_schedules_validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise ValueError("Schedule source-vintage checks failed")


if __name__ == "__main__":
    build()
