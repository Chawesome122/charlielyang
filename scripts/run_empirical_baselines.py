"""Two origin-safe descriptive MP mining-output exercises; no service forecast."""
from __future__ import annotations
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from weaponized.forecast.origins import run_backtests

ROOT = Path(__file__).resolve().parents[1]
FREEZE = date(2026, 10, 11)
ORIGINS = (date(2023, 12, 31), date(2024, 12, 31))
VARIABLE = "reported_output_year"
MINING_BASIS = "total_REO_content_in_concentrate"
UNIT = "metric_tonnes_per_observed_year"


def select_vintage(observations: pd.DataFrame, entity: str, origin: date, basis: str):
    """Filter disclosure first, then choose latest version per annual observation.

    Never count the same source's retrospective comparative annual column twice.
    Same-day conflicting versions are an unresolved adjudication, not averaged.
    """
    frame = observations[(observations["entity_id"] == entity)
        & (observations["variable"] == VARIABLE) & (observations["native_unit"] == UNIT)
        & (observations["product_basis"] == basis)].copy()
    for column in ("valid_date", "info_public_date"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    cutoff = pd.Timestamp(origin)
    frame = frame[(frame.info_public_date <= cutoff) & (frame.valid_date <= cutoff)
        & frame.value.notna() & (frame.observation_status == "company-reported")]
    if frame.empty:
        return frame
    if np.any(~np.isfinite(frame.value.astype(float))) or np.any(frame.value.astype(float) < 0):
        raise ValueError("Annual production must be finite and nonnegative")
    selected = []
    for _, group in frame.groupby("observation_id", sort=True):
        latest = group[group.info_public_date == group.info_public_date.max()]
        if latest.value.astype(float).nunique() > 1:
            raise ValueError("Conflicting equally dated source versions require adjudication")
        selected.append(latest.sort_values("record_version_id").iloc[-1])
    result = pd.DataFrame(selected).sort_values("valid_date").reset_index(drop=True)
    if result.valid_date.dt.year.duplicated().any():
        raise ValueError("Duplicate annual entity/product observations after version selection")
    return result


def baseline_predictions(training, target_year):
    years = training.valid_date.dt.year.to_numpy(dtype=float)
    values = training.value.to_numpy(dtype=float)
    if not len(values):
        return {}, {"all": "no_origin_eligible_annual_observations"}
    if target_year <= years[-1]:
        raise ValueError("Target must follow the last observed year")
    predictions = {"zero_new_build_persistence": float(values[-1]), "historical_mean": float(values.mean())}
    blocked = {}
    if len(values) >= 3 and len(np.unique(years)) == len(years):
        coefficients = np.polyfit(years - years[0], values, 1)
        predictions["linear_trend"] = float(max(0, np.polyval(coefficients, target_year - years[0])))
    else:
        blocked["linear_trend"] = "fewer_than_three_unique_annual_training_observations"
    # A physical carrying capacity cannot be guessed from the same tiny output
    # history, and a logistic curve with unknown level needs >=3 parameters.
    # This preregistered conservative baseline gate requires >=6 distinct years.
    if len(values) < 6:
        blocked["aggregate_logistic"] = "fewer_than_six_unique_annual_observations_and_no_independently_fixed_carrying_capacity"
    else:
        blocked["aggregate_logistic"] = "unknown_output_carrying_capacity_requires_registered_identification_analysis"
    return predictions, blocked


def run(observations_path=None, output_directory=None):
    observations_path = Path(observations_path or ROOT / "data/processed/rare_earths/observations.csv")
    out = Path(output_directory or ROOT / "outputs/empirical/rare_earths")
    out.mkdir(parents=True, exist_ok=True)
    observations = pd.read_csv(observations_path)
    frozen = select_vintage(observations, "MP_MountainPass_mine", FREEZE, MINING_BASIS)
    rows, audit, blocked_rows = [], [], []
    for origin in ORIGINS:
        target_year = origin.year + 1
        training = select_vintage(observations, "MP_MountainPass_mine", origin, MINING_BASIS)
        actual_rows = frozen[frozen.valid_date.dt.year == target_year]
        if len(actual_rows) != 1:
            blocked_rows.append({"origin": str(origin), "target_year": target_year, "component": "mining_output",
                "reason": "no_unique_freeze_eligible_actual"})
            continue
        actual = actual_rows.iloc[0]
        predictions, unavailable = baseline_predictions(training, target_year)
        train_path = out / f"baseline_training_{origin.year}.csv"
        training.to_csv(train_path, index=False, date_format="%Y-%m-%d")
        vintage_id = hashlib.sha256(train_path.read_bytes()).hexdigest()
        registry_key = (str(origin), 1)
        reference_name = "zero_new_build_persistence"
        # Fixed untuned rules are retrospectively registered now. Their source
        # data pass origin masks; this is not a prospectively registered forecast.
        registry = {registry_key: {"vintage_id": vintage_id, "prediction_as_of": str(origin),
            "input_info_public_dates": [t.date().isoformat() for t in training.info_public_date],
            "prediction": lambda prediction=predictions[reference_name]: prediction,
            "outcome": lambda observed=float(actual.value): observed, "predictions": predictions}}
        baseline_set = {name: (lambda registered, key=name: registered["predictions"][key])
            for name in predictions if name != reference_name}
        report = run_backtests(registry, [(origin, 1)],
            {registry_key: actual.info_public_date.date()}, {"freeze": FREEZE, "outcome_type": "continuous"}, baseline_set)[0]
        audit.append(report)
        if not report["scoreable"]:
            raise RuntimeError(f"Origin-vintage scoring refused: {report}")
        for name, prediction in predictions.items():
            score = report["model"] if name == reference_name else report["baselines"][name]
            rows.append({"origin": str(origin), "target_year": target_year,
                "entity_id": "MP_MountainPass_mine", "product_basis": MINING_BASIS, "native_unit": UNIT,
                "baseline": name, "prediction": prediction, "actual": float(actual.value),
                "signed_error": prediction - float(actual.value), **score,
                "training_n_unique_years": len(training), "last_observed_year": training.valid_date.dt.year.max(),
                "extrapolation_years_from_last_observed": target_year - training.valid_date.dt.year.max(),
                "training_vintage_sha256": vintage_id, "actual_record_version_id": actual.record_version_id,
                "actual_info_public_date": actual.info_public_date.date().isoformat(),
                "evaluation_kind": "retrospective_descriptive_two_origin_exercise"})
        blocked_rows.extend({"origin": str(origin), "target_year": target_year, "component": name,
            "reason": reason} for name, reason in unavailable.items())
        # Separation is a distinct native product; a 0/1-observation sample
        # cannot estimate trend, transition, ramp or completion uncertainty.
        separated = select_vintage(observations, "MP_MountainPass_separation", origin, "finished_packaged_NdPr_oxide")
        blocked_rows.append({"origin": str(origin), "target_year": target_year, "component": "NdPr_separation",
            "training_n_unique_years": len(separated),
            "reason": "too_few_training_observations_for_inferential_model; no_substitution_of_mining_REO"})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "baseline_scores.csv", index=False)
    if not frame.empty:
        summary = frame.groupby("baseline").agg(n_origins=("origin", "nunique"),
            mean_absolute_error=("absolute_error", "mean"), mean_squared_error=("squared_error", "mean")).reset_index()
        summary["interpretation"] = "descriptive_n_2_single_mine_no_statistical_skill_claim"
        summary.to_csv(out / "baseline_summary.csv", index=False)
    payload = {"freeze": str(FREEZE), "research_type": "empirical_company_reported_output_descriptive_hindcast",
        "n_origins": len(ORIGINS), "origins": [str(o) for o in ORIGINS], "horizon_years_from_origin": 1,
        "source_dataset_sha256": hashlib.sha256(observations_path.read_bytes()).hexdigest(),
        "product_scope": MINING_BASIS, "unit": UNIT,
        "limitations": ["Two extra micro origins, outside the blueprint's system-level 2/4/6-year schedule",
            "Retrospectively registered untuned baselines; no prospective model-selection or forecast-skill certification",
            "Company-reported output; no independent operating-output corroboration",
            "Conservative verified source availability may omit earlier public information",
            "Repeated source versions are not independent observations",
            "Annual total REO in concentrate is not NdPr output, China-free processing, alloy, qualified magnets, or physical service",
            "No stochastic production model, calibrated forecast distribution, or uncertainty intervals estimated"],
        "blocked": blocked_rows, "vintage_scoring_audit": audit}
    (out / "baseline_audit.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(summary.to_string(index=False) if not frame.empty else "No scoreable empirical output observations")
    return frame, payload


if __name__ == "__main__":
    run()
