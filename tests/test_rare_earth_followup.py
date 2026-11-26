from datetime import date
import json
from pathlib import Path

import pytest

from weaponized.rare_earths.followup import (
    capacity_cells,
    compare_capacities,
    donald_as_of,
    extract_claims,
    source_clocks,
    verified_html,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sources():
    entries = json.loads((ROOT / "metadata/rare_earth_followup_sources.json").read_text())
    return {row["source_id"]: row for row in entries}


def test_filing_index_binds_exact_document(sources):
    key = "RE-FU-EF-Q2-HTML"
    clocks = source_clocks(ROOT, sources)
    assert clocks[key]["info_public_date"] == "2026-08-05"
    assert clocks[key]["public_clock_source_id"] == "RE-FU-EF-Q2-INDEX"
    wrong = sources[key] | {"source_url": sources[key]["source_url"].replace("20260630", "20260930")}
    with pytest.raises(ValueError, match="exactly one filing"):
        source_clocks(ROOT, sources | {key: wrong})


def test_feasibility_report_public_clock_requires_exact_issuer_link(sources):
    key = "RE-FU-EF-BFS-PDF"
    clocks = source_clocks(ROOT, sources)
    assert clocks[key]["info_public_date"] == "2026-01-15"
    assert clocks[key]["public_clock_source_id"] == "RE-FU-EF-BFS-RELEASE"
    wrong = sources[key] | {"source_url": sources[key]["source_url"].replace("v1.pdf", "v2.pdf")}
    with pytest.raises(ValueError, match="exact dated release link"):
        source_clocks(ROOT, sources | {key: wrong})


def test_pdf_claim_requires_page_and_present_bytes(sources):
    key = "RE-FU-ATR-SEP30"
    clocks = source_clocks(ROOT, sources)
    spec = next(row for row in json.loads((ROOT / "codebooks/rare_earth_followup_claims.json").read_text())
                if row["claim_id"] == "FU:donald_q4_target")
    with pytest.raises(ValueError, match="Explicit source page required"):
        extract_claims(ROOT, [spec | {"locator": "Project update"}], sources, clocks)
    corrupt = sources[key] | {"sha256": "0" * 64}
    with pytest.raises(ValueError, match="checksum mismatch"):
        extract_claims(ROOT, [spec], sources | {key: corrupt}, clocks)


def test_donald_revision_can_be_visible_before_its_target_window():
    previous = dict(claim_id="q3", info_public_date="2026-08-05", event_date_upper="2026-09-30")
    revision = dict(claim_id="q4", info_public_date="2026-09-30", event_date_upper="2026-12-31")
    origins = [date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 11)]
    rows = donald_as_of(origins, [previous, revision])
    assert [row["latest_target_claim"] for row in rows] == ["q3", "q4", "q4"]
    assert all(row["actual_fid_date"] is None for row in rows)
    with pytest.raises(ValueError, match="before the freeze"):
        donald_as_of([date(2026, 10, 12)], [previous, revision])


def test_capacity_comparison_preserves_dashes_and_conflicting_native_values(sources):
    soup = verified_html(ROOT, sources["RE-FU-EF-Q2-HTML"])
    cells = capacity_cells(soup)
    assert len(cells) == 12
    assert sum(row["displayed_dash"] and row["value"] is None for row in cells) == 3
    july = {"tb": 20, "dy": 120}
    comparisons = compare_capacities(
        cells, {"tb": 12, "dy": 35}, july, july, {"ndpr": 6294, "tb": 80, "dy": 288},
    )
    assert [r["august_phase1_prose_minus_table"] for r in comparisons] == [None, 6, 72]
    assert [r["july_combined_prose_minus_august_table"] for r in comparisons] == [65, 0, 0]
    assert all(row["selected_operating_capacity"] is None for row in comparisons)
    header = next(cell for cell in soup.select("td") if cell.get_text(strip=True) == "NdPr (tpa)")
    header.string = "NdPr (kg)"
    with pytest.raises(ValueError, match="native capacity units"):
        capacity_cells(soup)
