"""Checks the actual archived industrial data, not synthetic fixture arithmetic."""
import json
from pathlib import Path
import pandas as pd
from weaponized.io.archive import sha256_file
from weaponized.io.vintages import select_asof

ROOT = Path(__file__).resolve().parents[1]


def test_claims_resolve_to_immutable_eligible_sources():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv")
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    assert len(frame) > 0
    for row in frame.itertuples():
        src = sources[row.source_id]
        assert sha256_file(ROOT/src["archive_path"]) == row.source_sha256
        assert row.info_public_date <= "2026-10-11"
        assert pd.notna(row.locator) and len(row.quote) > 10
        assert row.evidence_class == "empirical"
        assert src.get("publication_date") == row.info_public_date


def test_mp_annual_and_quarter_totals_agree_within_same_vintage():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv")
    frame = frame[frame.source_id.str.startswith("RE-MP-")]
    frame["year"] = pd.to_datetime(frame.valid_date).dt.year
    checked = 0
    for (_, _, _), subset in frame.groupby(["source_id", "entity_id", "year"]):
        annual = subset[subset.variable == "reported_output_year"]
        quarters = subset[subset.variable == "reported_output_quarter"]
        if len(annual) == 1 and len(quarters) == 4 and quarters.value.notna().all():
            assert quarters.value.astype(float).sum() == float(annual.value.iloc[0])
            checked += 1
    assert checked >= 6


def test_real_2023_output_is_unavailable_at_2023_forecast_origin():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv")
    panel = frame[(frame.entity_id == "MP_MountainPass_separation") & (frame.variable == "reported_output_year")]
    old = select_asof(panel, "2023-12-31")
    assert not ((old.valid_date == "2023-12-31") & old.value.notna()).any()
    current = select_asof(panel, "2026-10-11").set_index("valid_date")
    assert float(current.loc["2023-12-31", "value"]) == 200
    assert float(current.loc["2024-12-31", "value"]) == 1294
    assert float(current.loc["2025-12-31", "value"]) == 2599
