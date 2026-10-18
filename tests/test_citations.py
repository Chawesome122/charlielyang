"""Audit actual archived bibliography evidence, not the blueprint's status flags."""
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_citation_evidence_hashes_and_prefreeze_publication_records():
    rows = list(csv.DictReader((ROOT / "metadata/citation_audit.csv").open()))
    assert {row["source_id"] for row in rows} == {f"R{i:02d}" for i in range(1, 41)}
    for row in rows:
        if row["evidence_path"]:
            path = ROOT / row["evidence_path"].split(";")[0]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["evidence_sha256"]
        if row["metadata_deposited"]:
            assert row["first_published"] <= "2026-10-11"
            assert row["metadata_deposited"][:10] <= "2026-10-11"
            assert row["freeze_eligible"] == "True"


def test_conflicting_metadata_and_abstract_limits_remain_visible():
    rows = {row["source_id"]: row for row in csv.DictReader((ROOT / "metadata/citation_audit.csv").open())}
    assert rows["R11"]["metadata_status"] == "CONFLICT_REQUIRES_ORIGINAL"
    assert rows["R08"]["metadata_status"] == "PARTIAL_AUTHOR_MISSING"
    # A publisher-deposited abstract is admissible only for what its abstract says.
    for source in ("R01", "R03", "R05", "R06", "R07"):
        assert rows[source]["claim_status"] == "PUBLISHER_DEPOSITED_ABSTRACT_READ"
        assert rows[source]["evidence_excerpt"]
    assert rows["R02"]["claim_status"] == "ORIGINAL_TEXT_READ_FOR_CLAIM"
