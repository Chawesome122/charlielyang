"""Claim extraction must fail closed when the original or its evidence changes."""
import subprocess

import pytest

from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text, verify_original_quote


def test_poisoned_derivative_cannot_supply_a_claim(tmp_path):
    source = tmp_path/"original.html"
    source.write_text("<main>Observed output 38 tonnes.</main>")
    source.with_suffix(".extracted.txt").write_text("Observed output 3800 tonnes.")
    digest = sha256_file(source)
    assert verify_original_quote(source, digest, "Observed output 38 tonnes.")
    assert not verify_original_quote(source, digest, "Observed output 3800 tonnes.")


def test_cache_hit_does_not_hide_later_original_corruption(tmp_path):
    source = tmp_path/"report.html"
    source.write_text("<p>Output 38 tonnes</p>")
    digest = sha256_file(source)
    assert "38" in verified_original_text(source, digest)
    source.write_text("<p>Output 99 tonnes</p>")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_original_text(source, digest)


def test_hidden_scripts_are_not_report_body_evidence(tmp_path):
    source = tmp_path/"report.html"
    source.write_text('<script>operating 999 tonnes</script><style>fake evidence</style><p>Cash (10,000)\nUSD</p>')
    digest = sha256_file(source)
    assert not verify_original_quote(source, digest, "operating 999 tonnes")
    assert verify_original_quote(source, digest, "Cash (10,000) USD")
    assert not verify_original_quote(source, digest, "Cash 10,000 USD")


def test_pdf_page_locator_is_enforced(tmp_path, monkeypatch):
    source = tmp_path/"report.pdf"
    source.write_bytes(b"%PDF-test fixture; Poppler response mocked")
    calls = []
    def extract(command, **kwargs):
        calls.append(command)
        assert command[-2:] == ["-", "-"] and kwargs["input"] == source.read_bytes()
        return b"First page 38 tonnes\fSecond page 75 tonnes\f"
    monkeypatch.setattr(subprocess, "check_output", extract)
    digest = sha256_file(source)
    assert verify_original_quote(source, digest, "75 tonnes", 2)
    assert not verify_original_quote(source, digest, "75 tonnes", 1)
    assert len(calls) == 1 and calls[0][-1] == "-"
    for page in [0, -1, True, 1.5, 3, 99]:
        with pytest.raises(ValueError):
            verify_original_quote(source, digest, "75 tonnes", page)


def test_failed_pdf_extraction_is_not_replaced_by_sidecar(tmp_path, monkeypatch):
    source = tmp_path/"bad.pdf"
    source.write_bytes(b"%PDF damaged")
    source.with_suffix(".extracted.txt").write_text("Looks valid but is untrusted")
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "pdftotext")
    monkeypatch.setattr(subprocess, "check_output", fail)
    with pytest.raises(subprocess.CalledProcessError):
        verified_original_text(source, sha256_file(source))


def test_empty_quote_and_html_page_are_rejected(tmp_path):
    source = tmp_path/"report.html"
    source.write_text("<p>Report body</p>")
    digest = sha256_file(source)
    with pytest.raises(ValueError):
        verify_original_quote(source, digest, "  ")
    with pytest.raises(ValueError):
        verify_original_quote(source, digest, "Report body", 1)
