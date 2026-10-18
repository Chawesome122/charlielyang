"""Baselines and descriptive calibration; no claims from handfuls of origins."""
import numpy as np
from dataclasses import replace
from scipy.optimize import least_squares
from scipy.special import expit


def zero_new_build(last_observed, horizon):
    return np.full(horizon, float(last_observed))


def announced_on_time(activities, quarters, physical_bridge, ramp_model):
    """Optimistic schedule baseline, still subject to network constraints."""
    result = []
    for quarter in quarters:
        capacities = {}
        for p in activities:
            commission = p.commissioning_quarter if p.state == "O" else p.target_commission_quarter
            if commission is None and p.state != "X":
                raise ValueError("Missing announced date: on-time baseline not evaluable")
            capacities[p.activity_id] = ramp_model[p.activity_id].output_capacity(quarter, commission, p.state != "X")
        result.append(physical_bridge(quarter, capacities, {"physical": {}, "baseline": True})["served_fraction"])
    return np.asarray(result)


def historical_mean_delay(delays, *, min_completed=5):
    """Estimate only from origin-eligible completed projects; disclose selection bias."""
    values = np.asarray(delays, float)
    if len(values) < min_completed or not np.all(np.isfinite(values)):
        raise ValueError("Too few origin-eligible historical completions for mean-delay baseline")
    return float(values.mean())


def mean_delay_schedule(activities, quarters, physical_bridge, ramp_model, delays):
    """Announced commissioning shifted by origin-eligible historical mean delay.

    Completed-project-only delay samples are subject to survivor selection; this
    simple benchmark is retained precisely so that more elaborate models have a
    transparent comparator, not as an unbiased estimator of project completion.
    """
    delay = int(np.ceil(historical_mean_delay(delays)))
    shifted = [replace(p, target_commission_quarter=(p.target_commission_quarter + delay)
        if p.target_commission_quarter is not None else None) for p in activities]
    return announced_on_time(shifted, quarters, physical_bridge, ramp_model)


def linear_trend(times, values, future):
    t, y, f = np.asarray(times, float), np.asarray(values, float), np.asarray(future, float)
    if len(t) < 3 or len(t) != len(y) or len(np.unique(t)) != len(t):
        raise ValueError("At least three distinct observed time points required")
    coefficients = np.polyfit(t - t[0], y, 1)
    return np.clip(np.polyval(coefficients, f - t[0]), 0, 1)


def logistic_trend(times, values, future):
    """Aggregate descriptive baseline; not a physical supply-network forecast."""
    t, y, f = np.asarray(times, float), np.asarray(values, float), np.asarray(future, float)
    if len(t) < 6 or len(t) != len(y) or np.any((y < 0) | (y > 1)):
        raise ValueError("Six bounded historical service observations required")
    centered = t - t[0]
    result = least_squares(lambda b: expit(b[0] + b[1] * centered) - y, [0, 0],
        bounds=([-30, -10], [30, 10]))
    if not result.success or np.linalg.matrix_rank(result.jac) < 2:
        raise ValueError("Aggregate logistic trend not identified")
    return expit(result.x[0] + result.x[1] * (f - t[0]))


def reliability_bins(probabilities, outcomes, bins=5):
    p, y = np.asarray(probabilities, float), np.asarray(outcomes, float)
    if len(p) != len(y) or np.any((p < 0) | (p > 1)) or np.any((y != 0) & (y != 1)):
        raise ValueError("Invalid probabilities or outcomes")
    edges = np.linspace(0, 1, bins + 1)
    result = []
    for i in range(bins):
        mask = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= 1))
        result.append({"n": int(mask.sum()), "predicted": float(p[mask].mean()) if mask.any() else None,
            "observed": float(y[mask].mean()) if mask.any() else None})
    return {"bins": result, "interpretation": "descriptive; no calibration certification", "n": len(p)}


def cumulative_incidence(followup_time, event_cause, horizon, cause=1):
    """Aalen–Johansen marginal CIF with competing events and right censoring.

    Independent censoring is assumed; stratification/covariate adjustment and
    left truncation require an extended risk-set implementation. Tied event and
    censor times use the risk set just before that time (events before censors).
    """
    times, causes = np.asarray(followup_time, float), np.asarray(event_cause, int)
    if len(times) != len(causes) or not len(times) or np.any(~np.isfinite(times)) or np.any(times < 0) or np.any(causes < 0) or cause <= 0:
        raise ValueError("Invalid competing-risk follow-up")
    survival, cif = 1.0, 0.0
    for time in np.unique(times[times <= horizon]):
        risk = np.sum(times >= time)
        all_events = np.sum((times == time) & (causes > 0))
        target_events = np.sum((times == time) & (causes == cause))
        cif += survival * target_events / risk
        survival *= 1 - all_events / risk
    return {"cumulative_incidence": float(cif), "event_free_survival": float(survival),
        "n": len(times), "interpretation": "descriptive CIF under independent censoring"}
