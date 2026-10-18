"""Information-vintage and outcome-release masks; future endpoints never score."""
from datetime import date
import calendar

FREEZE = date(2026, 10, 11)
RARE_EARTH_ORIGINS = tuple(date(year, 12, 31) for year in (2016, 2018, 2020, 2022, 2024))


def endpoint(origin: date, years: int) -> date:
    year = origin.year + years
    return date(year, origin.month, min(origin.day, calendar.monthrange(year, origin.month)[1]))


def outcome_eligibility(origin: date, years: int, outcome_public_date: date | None,
                        freeze: date = FREEZE) -> dict:
    end = endpoint(origin, years)
    if end > freeze:
        reason = "future_endpoint"
    elif outcome_public_date is None:
        reason = "outcome_release_not_verified"
    elif outcome_public_date > freeze:
        reason = "outcome_not_public_by_freeze"
    elif outcome_public_date < end:
        reason = "outcome_cannot_confirm_unfinished_endpoint"
    else:
        reason = "eligible"
    return {"origin": origin.isoformat(), "horizon_years": years, "endpoint": end.isoformat(),
        "outcome_public_date": outcome_public_date.isoformat() if outcome_public_date else None,
        "scoreable": reason == "eligible", "reason": reason}


def vintage_rows(rows, origin: date, *, public_key="info_public_date"):
    """Publication date, not a retrospective event date, controls inclusion."""
    selected = []
    for row in rows:
        public = row.get(public_key)
        if public is None:
            continue
        public = date.fromisoformat(public) if isinstance(public, str) else public
        if public <= origin:
            selected.append(row)
    return selected


def run_backtests(vintage_registry, endpoints, outcome_release_registry,
                  scoring_config, baseline_set):
    """Execute only registered callable forecasts with released actual outcomes.

    Registry entries carry origin, years, prediction and outcome callables.
    Empty data produce explicit non-scoreable rows rather than fake scores.
    """
    from .scoring import binary_scores
    import numpy as np
    def score(prediction, observed):
        if scoring_config.get("outcome_type", "binary") == "binary":
            return binary_scores(prediction, observed)
        if scoring_config.get("outcome_type") != "continuous":
            raise ValueError("Unknown registered outcome_type")
        pred, actual = np.broadcast_arrays(np.asarray(prediction, float), np.asarray(observed, float))
        if pred.size == 0 or np.any(~np.isfinite(pred)) or np.any(~np.isfinite(actual)):
            raise ValueError("Continuous scores require finite nonempty observations and predictions")
        return {"absolute_error": float(np.mean(abs(pred - actual))),
                "squared_error": float(np.mean((pred - actual) ** 2)), "n": pred.size}
    results = []
    freeze = scoring_config.get("freeze", FREEZE)
    for origin, years in endpoints:
        key = (origin.isoformat(), years)
        row = outcome_eligibility(origin, years, outcome_release_registry.get(key), freeze)
        registered = vintage_registry.get(key)
        if row["scoreable"] and registered is None:
            row.update(scoreable=False, reason="historical_vintage_not_available")
        if row["scoreable"]:
            # The origin tuple alone cannot establish historical admissibility.
            # Every input release (including labels, model selection, project
            # universe and covariates) must be registered in this source clock.
            publications = registered.get("input_info_public_dates")
            as_of = registered.get("prediction_as_of")
            vintage_id = registered.get("vintage_id")
            if (not isinstance(vintage_id, str) or not vintage_id.strip() or not as_of
                    or not isinstance(publications, (list, tuple)) or not publications
                    or not callable(registered.get("prediction")) or not callable(registered.get("outcome"))):
                row.update(scoreable=False, reason="prediction_vintage_not_auditable")
            else:
                try:
                    as_of = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
                    dates = [date.fromisoformat(value) if isinstance(value, str) else value for value in publications]
                    valid_dates = isinstance(as_of, date) and all(isinstance(value, date) for value in dates)
                    if not valid_dates:
                        row.update(scoreable=False, reason="prediction_vintage_not_auditable")
                    elif as_of > origin or any(value > as_of for value in dates):
                        row.update(scoreable=False, reason="prediction_vintage_leakage")
                    else:
                        row["vintage_id"] = vintage_id
                        row["prediction_as_of"] = as_of.isoformat()
                        row["latest_input_public_date"] = max(dates).isoformat()
                except (TypeError, ValueError):
                    row.update(scoreable=False, reason="prediction_vintage_not_auditable")
        if row["scoreable"]:
            pred, observed = registered["prediction"](), registered["outcome"]()
            row["model"] = score(pred, observed)
            row["baselines"] = {name: score(fn(registered), observed) for name, fn in baseline_set.items()}
        results.append(row)
    return results
