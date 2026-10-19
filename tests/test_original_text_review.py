"""Independent adversarial cache and actual explicit-page source review."""
import json
from pathlib import Path
import re

import pandas as pd
import pytest

from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text, verify_original_quote

ROOT = Path(__file__).resolve().parents[1]


def test_same_path_new_digest_reextracts_and_old_digest_remains_fail_closed(tmp_path):
    source = tmp_path/"original.html"
    source.write_text("<p>Output 38 tonnes</p>")
    first_digest = sha256_file(source)
    assert verify_original_quote(source, first_digest, "Output 38 tonnes")
    source.write_text("<p>Output 99 tonnes</p>")
    second_digest = sha256_file(source)
    assert verify_original_quote(source, second_digest, "Output 99 tonnes")
    assert not verify_original_quote(source, second_digest, "Output 38 tonnes")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_original_text(source, first_digest)
    source.write_text("<p>Output 38 tonnes</p>")
    assert verify_original_quote(source, first_digest, "Output 38 tonnes")


def test_actual_explicit_pdf_page_locators_match_the_fresh_hashed_original():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").fillna("").to_dict("records"):
        sources[row["source_id"]] = row
    checked = 0
    for table in ["industrial_evidence/project_milestones.csv", "rare_earths/project_state_evidence.csv"]:
        for row in pd.read_csv(ROOT/"data/processed"/table).fillna("").to_dict("records"):
            match = re.fullmatch(r"PDF page ([1-9][0-9]*)", row["locator"])
            if not match:
                continue
            source = sources[row["source_id"]]
            assert row["source_sha256"] == source["sha256"]
            assert verify_original_quote(ROOT/source["archive_path"], source["sha256"], row["quote"], int(match[1]))
            checked += 1
    assert checked == 33


def test_pdf_snapshot_survives_path_replacement_during_extraction(tmp_path, monkeypatch):
    import subprocess

    source = tmp_path/"report.pdf"
    original = b"%PDF mocked original byte snapshot 38 tonnes"
    source.write_bytes(original)
    digest = sha256_file(source)
    seen = []

    def extract(command, **kwargs):
        # The exact bytes just hashed must be passed to Poppler, rather than
        # reopening a path that may change between verification and extraction.
        assert kwargs["input"] == original
        assert command[-2:] == ["-", "-"]
        source.write_bytes(b"%PDF replaced byte snapshot 999 tonnes")
        seen.append(command)
        return b"Original output 38 tonnes\f"

    monkeypatch.setattr(subprocess, "check_output", extract)
    assert "Original output 38 tonnes" in verified_original_text(source, digest)
    assert len(seen) == 1
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_original_text(source, digest)


def test_explicit_locator_supplies_page_and_conflicting_fields_fail_closed():
    from weaponized.io.original_text import evidence_pdf_page

    assert evidence_pdf_page({"locator":"PDF page 20"}) == 20
    assert evidence_pdf_page({"pdf_page":"", "locator":"PDF page 3"}) == 3
    assert evidence_pdf_page({"pdf_page":20, "locator":"PDF page 20"}) == 20
    assert evidence_pdf_page({"locator":"10-K Business; paragraph"}) is None
    with pytest.raises(ValueError):
        evidence_pdf_page({"pdf_page":1, "locator":"PDF page 20"})


@pytest.mark.parametrize("row", [
    {"pdf_page":True}, {"pdf_page":0}, {"pdf_page":-1}, {"pdf_page":1.5},
    {"locator":"PDF page 0"}, {"locator":"PDF page -1"}, {"locator":"PDF page 1.5"},
])
def test_invalid_or_fractional_page_fields_cannot_silently_become_other_pages(row):
    from weaponized.io.original_text import evidence_pdf_page

    with pytest.raises(ValueError):
        evidence_pdf_page(row)
