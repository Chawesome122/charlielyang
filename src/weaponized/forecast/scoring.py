"""Proper forecast scores and explicit four-quarter first-passage conventions."""
import numpy as np


def binary_scores(probability, outcome):
    p, y = np.asarray(probability, dtype=float), np.asarray(outcome, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)) or np.any((y != 0) & (y != 1)):
        raise ValueError("Probabilities in [0,1] and binary outcomes required")
    p, y = np.broadcast_arrays(p, y)
    # Endpoint correct forecasts have score zero; incorrect certainty has infinite penalty.
    correct_probability = np.where(y == 1, p, 1 - p)
    with np.errstate(divide="ignore"):
        log = -np.log(correct_probability)
    return {"brier": float(np.mean((p - y) ** 2)), "negative_log_score": float(np.mean(log)), "n": p.size}


def crps_ensemble(samples, observation):
    """Exact unweighted empirical CRPS in O(N log N), retaining native units."""
    x = np.sort(np.asarray(samples, dtype=float))
    if x.ndim != 1 or not len(x) or not np.all(np.isfinite(x)) or not np.isfinite(observation):
        raise ValueError("Finite nonempty one-dimensional ensemble required")
    n = len(x)
    pairwise_half = np.sum((2 * np.arange(1, n + 1) - n - 1) * x) / n ** 2
    return float(np.mean(np.abs(x - observation)) - pairwise_half)


def interval_coverage(samples, observation, levels=(0.5, 0.8, 0.95)):
    values = np.asarray(samples, dtype=float)
    result = {}
    for level in levels:
        if not 0 < level < 1:
            raise ValueError("Coverage level must lie in (0,1)")
        lower, upper = np.quantile(values, [(1 - level) / 2, (1 + level) / 2])
        result[str(level)] = {"lower": float(lower), "upper": float(upper),
            "covered": bool(lower <= observation <= upper)}
    return result


def time_dependent_brier(probability, followup_time, event_cause, horizon, cause,
                         censor_survival):
    """IPCW Brier for cause-specific cumulative incidence with right censoring.

    Cause 0 denotes censoring, positive codes are competing realized events.
    `censor_survival(t, left_limit)` must be estimated from an eligible risk set
    under the assumed conditional-independent censoring mechanism. Competing
    events are observed zeros, not censored commissioning events. No IPCW claim
    is valid when censoring depends on unmeasured risk or G is near zero.
    """
    p, t, c = np.asarray(probability, float), np.asarray(followup_time, float), np.asarray(event_cause, int)
    p, t, c = np.broadcast_arrays(p, t, c)
    if cause <= 0 or horizon < 0 or np.any(~np.isfinite(p)) or np.any(~np.isfinite(t)) or np.any(t < 0) or np.any((p < 0) | (p > 1)) or np.any(c < 0):
        raise ValueError("Invalid probabilities, times or cause codes")
    contributions = []
    observed = 0
    max_weight = 0.0
    for pred, time, event in zip(p.ravel(), t.ravel(), c.ravel()):
        if time <= horizon and event == 0:
            contributions.append(0.0)
            continue
        before = time <= horizon
        g = float(censor_survival(time if before else horizon, before))
        if not np.isfinite(g) or not 0 < g <= 1:
            raise ValueError("Censor survival must be in (0,1]; no supported inverse weight")
        y = float(before and event == cause)
        weight = 1 / g
        contributions.append(weight * (pred - y) ** 2)
        max_weight = max(max_weight, weight)
        observed += 1
    return {"ipcw_brier": float(np.mean(contributions)), "n": p.size,
        "known_status_n": observed, "max_inverse_censor_weight": max_weight,
        "assumption": "conditional independent censoring and correctly specified censor survival"}


def persistence_times(service, quarters, threshold, consecutive=4, service_atol=1e-8):
    y, q = np.asarray(service, float), np.asarray(quarters, int)
    if y.ndim == 1:
        y = y[None, :]
    if y.shape[1] != len(q) or np.any(np.diff(q) != 1) or not 0 <= threshold <= 1 or consecutive < 1:
        raise ValueError("Invalid quarterly service panel or threshold")
    if np.any(~np.isfinite(y)) or np.any((y < -1e-9) | (y > 1 + 1e-9)):
        raise ValueError("Service must be finite within [0,1]")
    starts = np.full(len(y), np.inf)
    recognition = np.full(len(y), np.inf)
    for index in range(max(0, len(q) - consecutive + 1)):
        first = np.isinf(starts) & np.all(y[:, index:index + consecutive] >= threshold - service_atol, axis=1)
        starts[first], recognition[first] = q[index], q[index + consecutive - 1]
    return starts, recognition


def empirical_quantiles_with_infinity(values, probabilities=(0.05, 0.25, 0.5, 0.75, 0.95)):
    """Inverse empirical CDF, preserving no-crossing mass (JSON null + flag)."""
    x = np.sort(np.asarray(values, dtype=float))
    if not len(x):
        raise ValueError("Empty event sample")
    result = {}
    for probability in probabilities:
        if not 0 < probability <= 1:
            raise ValueError("Quantile probability must be in (0,1]")
        value = x[max(0, int(np.ceil(probability * len(x))) - 1)]
        result[str(probability)] = {"quarter_index": int(value) if np.isfinite(value) else None,
            "no_crossing_within_horizon": bool(np.isinf(value))}
    return result


def probability_summary(events, effective_sample_size=None, tolerance=0.005):
    events = np.asarray(events)
    if events.dtype.kind not in "buif" or np.any(~np.isfinite(events)) or np.any((events != 0) & (events != 1)):
        raise ValueError("Monte Carlo event indicators must be finite boolean or binary numeric values")
    events = events.astype(bool)
    if events.size == 0:
        raise ValueError("No Monte Carlo draws")
    n = events.size if effective_sample_size is None else float(effective_sample_size)
    if n <= 0 or n > events.size:
        raise ValueError("Invalid effective sample size")
    if tolerance <= 0 or not np.isfinite(tolerance):
        raise ValueError("Monte Carlo tolerance must be finite and positive")
    p = float(events.mean())
    se = float(np.sqrt(p * (1 - p) / n))
    worst_case_se = float(.5 / np.sqrt(n))
    # Wilson interval also exposes uncertainty when zero events are observed.
    z = 1.959963984540054
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"probability": p, "mc_standard_error": se, "n": events.size,
        "effective_sample_size": n, "worst_case_mc_standard_error": worst_case_se,
        "mc_tolerance_met": se <= tolerance and worst_case_se <= tolerance,
        "mc_wilson_95": [float(max(0, center - radius)), float(min(1, center + radius))]}


def summarize_thresholds(panel, targets, thresholds=(0.5, 0.75, 0.9, 1.0), consecutive=4):
    rows = []
    for threshold in thresholds:
        starts, recognition = persistence_times(panel.served_fraction, panel.quarters, threshold, consecutive)
        for target in targets:
            if target + consecutive - 1 > panel.quarters[-1]:
                raise ValueError("Start-by-target requires lookahead through target+3, otherwise right-censored")
            if target not in panel.quarters:
                raise ValueError("Target outside simulation horizon")
            rows.append({"threshold": threshold, "target_quarter_index": int(target),
                "start_by_target": probability_summary(starts <= target),
                "recognized_by_target": probability_summary(recognition <= target),
                "start_quantiles": empirical_quantiles_with_infinity(starts),
                "recognition_quantiles": empirical_quantiles_with_infinity(recognition)})
    return rows
