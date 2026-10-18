from pathlib import Path
import importlib.util
from datetime import date
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("empirical_baselines", ROOT / "scripts/run_empirical_baselines.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_actual_sources_respect_publication_lag_and_duplicate_versions():
    data = pd.read_csv(ROOT / "data/processed/rare_earths/observations.csv")
    origin = module.select_vintage(data, "MP_MountainPass_mine", date(2023, 12, 31), module.MINING_BASIS)
    assert origin.valid_date.dt.year.tolist() == [2020, 2021, 2022]
    later = module.select_vintage(data, "MP_MountainPass_mine", date(2024, 12, 31), module.MINING_BASIS)
    assert later.valid_date.dt.year.tolist() == [2020, 2021, 2022, 2023]
    assert len(later) < len(data[(data.entity_id == "MP_MountainPass_mine") & (data.variable == "reported_output_year")])
    predictions, blocked = module.baseline_predictions(origin, 2024)
    # Fit through 2022, but target 2024: two years beyond last released output.
    assert predictions["linear_trend"] == pytest.approx(47132.3333333333)
    assert "aggregate_logistic" in blocked


def test_empirical_two_origin_end_to_end(tmp_path):
    scores, audit = module.run(output_directory=tmp_path)
    assert scores.origin.nunique() == 2 and len(scores) == 6
    assert scores[scores.target_year == 2024].actual.unique().tolist() == [45455]
    assert scores[scores.target_year == 2025].actual.unique().tolist() == [50692]
    assert set(scores.extrapolation_years_from_last_observed) == {2}
    assert all(entry["scoreable"] for entry in audit["vintage_scoring_audit"])
    separation = [entry for entry in audit["blocked"] if entry["component"] == "NdPr_separation"]
    assert [entry["training_n_unique_years"] for entry in separation] == [0, 1]
    assert (tmp_path / "baseline_training_2023.csv").exists()
