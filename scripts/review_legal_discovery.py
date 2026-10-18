"""Validate manual scope screening of the additional archived legal corpus.

Screening does not establish a complete technical crosswalk or current law.
Administrative deadlines and proposed rules are not enacted access losses.
"""
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.semiconductors.legal import issued_xml_text

ROOT = Path(__file__).resolve().parents[1]


def main():
    log = ROOT/"metadata/legal_discovery_acquisitions.jsonl"
    records = {r["source_id"]:r for r in map(json.loads, log.read_text().splitlines()) if r["status"] == "downloaded"}
    specs = pd.read_csv(ROOT/"codebooks/legal_discovery_screening.csv").fillna("")
    if specs.document_number.duplicated().any():
        raise ValueError("One scope-screen decision per original document required")
    texts = {sid for sid in records if sid.endswith("-TEXT")}
    if set(specs.source_id) != texts:
        raise ValueError("Additional archive screening coverage incomplete")
    events = pd.read_csv(ROOT/"data/processed/semiconductors/legal_events.csv")
    reviewed = set(events.policy_id.str.removeprefix("SC-US-"))
    output = []
    for item in specs.to_dict("records"):
        source = records[item["source_id"]]
        raw = (ROOT/source["archive_path"]).read_bytes()
        if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
            raise ValueError("Original legal XML checksum mismatch")
        text = issued_xml_text(raw, item["document_number"])
        if item["required_text"] not in text:
            raise ValueError(f"Scope-screen quote absent: {item['document_number']}")
        metadata = records[item["source_id"].replace("-TEXT", "-META")]
        if sha256_file(ROOT/metadata["archive_path"]) != metadata["sha256"]:
            raise ValueError("Original legal metadata checksum mismatch")
        meta = json.loads((ROOT/metadata["archive_path"]).read_text())
        public = meta["publication_date"]
        match = re.search(r"\[FR Doc\. [^\]]+ Filed (\d{1,2}-\d{1,2}-\d{2});", text)
        from datetime import datetime
        first = datetime.strptime(match[1], "%m-%d-%y").date().isoformat() if match else public
        if max(first, public) > "2026-10-11":
            raise ValueError("Post-freeze legal document cannot enter screening")
        admitted = item["document_number"] in reviewed
        if (item["decision"] == "ADDED_TO_REVIEWED_EVENT_CORPUS") != admitted:
            raise ValueError("Scope-screen/admitted chronology inconsistency")
        output.append(item | dict(publication_date=public, info_public_date=first, source_sha256=source["sha256"],
                                  in_reviewed_event_corpus=admitted, current_law_consolidation_verified=False,
                                  numeric_access_effect_identified=False))
    frame = pd.DataFrame(output)
    frame.to_csv(ROOT/"data/processed/semiconductors/legal_discovery_screening.csv", index=False)
    summary = dict(passed=True, original_additional_documents=len(frame),
                   decision_counts=frame.decision.value_counts().to_dict(),
                   reviewed_event_phases=len(events), original_FR_documents_in_reviewed_corpus=int(events[events.jurisdiction.eq("US")].policy_id.nunique()),
                   current_law_consolidated=False, independent_legal_review=False,
                   numeric_foreign_access_losses_identified=False)
    (ROOT/"outputs/diagnostics/legal_discovery_screening_validation.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
