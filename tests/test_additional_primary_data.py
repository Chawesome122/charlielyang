from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_lynas_native_output_and_public_dates():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_annual_production.csv")
    assert len(frame) == 22 and (frame.info_public_date <= "2026-10-11").all()
    assert frame.product_basis.nunique() == 2 and set(frame.stage) == {"separation"}
    values = frame.set_index(["period_end", "product_basis"]).value
    assert values["2024-06-30", "NdPr_oxide_product_family"] == 5655
    assert values["2025-06-30", "NdPr_oxide_product_family"] == 6558
    assert values["2026-06-30", "NdPr_oxide_product_family"] == 7260
    assert values["2026-06-30", "total_REO"] == 13089
    sources = pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").set_index("source_id")
    for row in frame.itertuples():
        source = sources.loc[row.source_id]
        assert hashlib.sha256((ROOT/source.archive_path).read_bytes()).hexdigest() == row.source_sha256
        assert source.publication_date == row.info_public_date


def test_project_history_has_failed_or_suspended_assets_and_no_fake_network():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths/project_state_evidence.csv")
    assert frame.project_id.nunique() >= 15
    assert (frame.state == "S").sum() >= 3
    assert not frame.commercial_network_ready.any()
    # Demonstration campaign tonnes cannot become a perpetually replenished rate.
    demo = frame[frame.activity_id == "RER_Upton_separation"].iloc[0]
    assert "TOTAL" in demo.native_unit and "not per year" in demo.native_unit
    saltend = frame[frame.project_id == "Pensana_Saltend"].iloc[0]
    assert not saltend.eligible_for_asof and pd.isna(saltend.info_public_date)
