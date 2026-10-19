"""Actual missing-source-clock masks and rejection of tempting metadata clocks."""
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.io.publication_extension import report_link_metadata, source_vintage_readiness

ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://issuer.example/reports/"
PDF = "https://issuer.example/files/2025.pdf"


def test_wrong_sibling_download_is_recorded_without_aliasing_the_exact_report():
    html = '<ul><li><a href="/files/2023.pdf">download</a><a href="/files/2025.pdf">Annual 2025</a></li><li><a href="/files/unrelated.pdf">Other</a></li></ul>'
    result = report_link_metadata(html, PAGE, PDF)
    assert result["exact_report_link_count"] == 1
    assert result["off_target_same_list_item_urls"] == ["https://issuer.example/files/2023.pdf"]
    assert result["exact_report_link_titles"] == ["Annual 2025"]


def test_nested_navigation_links_are_not_same_item_download_aliases():
    html = '<li><a href="/files/2025.pdf">Report</a><ul><li><a href="/sustainability">Menu</a></li></ul></li>'
    assert not report_link_metadata(html, PAGE, PDF)["off_target_same_list_item_urls"]


def test_generic_page_dates_stay_rejected_metadata_without_becoming_report_clocks():
    node = {"@type":"WebPage", "datePublished":"2020-08-17T11:04:24Z", "dateModified":"2025-10-15T08:09:24Z"}
    html = '<script type="application/ld+json">'+json.dumps(node)+'</script><a href="/files/2025.pdf">Annual 2025</a>'
    result = report_link_metadata(html, PAGE, PDF)
    assert len(result["rejected_page_date_candidates"]) == 2
    assert "info_public_date" not in result


def test_missing_clock_does_not_become_visible_despite_an_early_retrieval():
    row = source_vintage_readiness(None, "2024-01-01T01:02:03Z", "2025-12-31")
    assert row["status"] == "UNKNOWN_PUBLICATION_DATE"
    assert row["archive_retrieved_by_origin"]
    assert not row["source_reported_available"]


def test_source_stated_availability_does_not_certify_the_historical_bytes():
    row = source_vintage_readiness("2026-03-27", "2026-10-18T06:23:37Z", "2026-03-31")
    assert row["source_reported_available"]
    assert not row["archive_retrieved_by_origin"]
    assert not row["historical_byte_vintage_certified"]
    assert not row["independently_certified_historical_forecast_eligible"]


def test_pre_publication_origin_and_exact_day_boundary():
    assert source_vintage_readiness("2026-03-27", "2026-10-18T00:00:00Z", "2026-03-26")["status"] == "NOT_YET_PUBLIC"
    assert source_vintage_readiness("2026-03-27", "2026-10-18T00:00:00Z", "2026-03-27")["source_reported_available"]


def test_retrieval_clock_is_compared_in_utc():
    row = source_vintage_readiness("2025-12-31", "2026-01-01T00:30:00+02:00", "2025-12-31")
    assert row["archive_retrieved_by_origin"]


@pytest.mark.parametrize("public,retrieved,origin", [
    ("2026-10-12", "2026-10-18T00:00:00Z", "2026-10-11"),
    ("2026-03-27", "2026-10-18T00:00:00Z", "2026-10-12"),
    (None, "2026-10-18T00:00:00", "2026-10-11"),
])
def test_freeze_and_naive_retrieval_timestamp_are_rejected(public, retrieved, origin):
    with pytest.raises(ValueError):
        source_vintage_readiness(public, retrieved, origin)


def test_actual_source_origin_and_rejected_metadata_artifacts():
    out = ROOT/"data/processed/publication_extension"
    origins = pd.read_csv(out/"source_origin_readiness.csv")
    assert len(origins) == 48
    assert not origins.historical_byte_vintage_certified.any()
    assert not origins.independently_certified_historical_forecast_eligible.any()
    assert not origins.archive_retrieved_by_origin.any()
    rejected = pd.read_csv(out/"rejected_date_candidates.csv")
    assert len(rejected) == 18 and not rejected.admissible_as_publication.any()
    annual = pd.read_csv(out/"annual_clock_blockers.csv")
    assert len(annual) == 4 and annual.info_public_date.isna().all()
    for row in annual[annual.source_id.str.contains("PENSANA")].itertuples():
        assert json.loads(row.off_target_same_list_item_urls) == ["https://pensana.co.uk/wp-content/uploads/2023/10/Pensana-AR-2023.pdf"]


def test_actual_information_loss_masks_reject_retrospective_comparatives():
    table = pd.read_csv(ROOT/"data/processed/publication_extension/claim_origin_masking.csv").set_index("origin")
    assert table.loc["2025-12-31", "two_clock_information_available"] == 0
    assert table.loc["2025-12-31", "event_date_only_lookahead_claims"] == 15
    assert table.loc["2026-06-30", "event_date_only_lookahead_claims"] == 12
    assert table.loc["2026-10-11", "two_clock_information_available"] == 37
