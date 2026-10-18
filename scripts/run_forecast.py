"""Execute empirical readiness audit plus genuinely synthetic forecasting tests.

No toy value enters outputs/empirical or a real-world probability table.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import time
import numpy as np
os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from weaponized.rare_earths.projects import ProjectSnapshot, quarter_index, quarter_label
from weaponized.rare_earths.transitions import TransitionModel, fit_constant_intensities
from weaponized.rare_earths.ramps import RampSpec
from weaponized.rare_earths.simulate import CachedPhysicalBridge, simulate_projects
from weaponized.rare_earths.lp import solve_network
from weaponized.rare_earths.resilience import fixture_four_elements
from weaponized.forecast.origins import RARE_EARTH_ORIGINS, outcome_eligibility
from weaponized.forecast.scoring import summarize_thresholds, binary_scores, crps_ensemble
from weaponized.forecast.calibration import zero_new_build, announced_on_time, mean_delay_schedule, linear_trend, logistic_trend

ROOT = Path(__file__).resolve().parents[1]


def safe_json(value):
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    if isinstance(value, np.generic):
        return safe_json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return {"nonfinite": "positive_infinity" if value > 0 else "negative_infinity" if value < 0 else "nan"}
    return value


def write_json(path, data):
    path.write_text(json.dumps(safe_json(data), indent=2, allow_nan=False) + "\n")


def audit_empirical_readiness():
    path = ROOT / "outputs/diagnostics"
    path.mkdir(parents=True, exist_ok=True)
    missing = [
        "Defined historical project universe including cancelled/suspended projects and archived revisions",
        "Verified per-activity native capacities, ownership and material provenance as of each origin",
        "Verified element recipes, recovery yields, transport routes, finite feeds, inventories and magnet demand",
        "Project transition observations with event intervals, public dates and complete-surveillance/reporting assumptions",
        "Enough independent cause-specific transition events to estimate hazards and commissioning/ramp uncertainty",
        "Released historical physical-service outcomes and frozen training/model-selection vintages",
    ]
    readiness = {"freeze": "2026-10-11", "status": "BLOCKED",
        "empirical_probabilities_computed": False, "missing_requirements": missing,
        "reason": "Available project/source records do not establish a verified physical network and project risk set; no substitution of synthetic inputs permitted."}
    write_json(path / "forecast_readiness.json", readiness)
    with (path / "empirical_forecast_targets.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target", "threshold", "p_start_by_target",
            "p_recognized_by_target", "status", "reason"])
        writer.writeheader()
        for target in ["2028Q4", "2031Q4", "2035Q4"]:
            for threshold in [.5, .75, .9, 1.0]:
                writer.writerow({"target": target, "threshold": threshold, "p_start_by_target": "",
                    "p_recognized_by_target": "", "status": "BLOCKED", "reason": "verified_network_and_transition_risk_set_unavailable"})
    # A mechanical endpoint can be potentially eligible without an available released outcome.
    schedule = [outcome_eligibility(origin, horizon, None)
        for origin in RARE_EARTH_ORIGINS for horizon in (2, 4, 6)]
    write_json(path / "historical_backtest_eligibility.json", schedule)
    return readiness


def synthetic_network():
    """Three finite four-element four-stage chains, each a full supplier group.

    Upstream sites are conditionally already operating. Only each supplier's
    final magnet activity is in the illustrative commissioning risk set.
    """
    base = fixture_four_elements()
    suppliers = ("synthetic_A", "synthetic_B", "synthetic_C")
    facilities, activities, feeds, routes = [], [], [], []
    for supplier, scale in zip(suppliers, (1.0, 1.1, 1.2)):
        def node(value):
            return "bloc" if value == "bloc" else f"{supplier}_{value}"
        group = frozenset({supplier})
        facilities.extend(replace(f, id=node(f.id), groups=group) for f in base.facilities if f.id != "bloc")
        activities.extend(replace(a, id=f"{supplier}_{a.id}", node=node(a.node),
            groups=group, capacity=a.capacity * scale) for a in base.activities)
        feeds.extend(replace(f, id=f"{supplier}_{f.id}", node=node(f.node), groups=group,
            capacity=f.capacity * scale) for f in base.feeds)
        routes.extend(replace(r, id=f"{supplier}_{r.id}", source=node(r.source), target=node(r.target),
            groups=group, capacity=r.capacity * scale) for r in base.routes)
    facilities.append(next(f for f in base.facilities if f.id == "bloc"))
    return replace(base, facilities=tuple(facilities), activities=tuple(activities), feeds=tuple(feeds),
        routes=tuple(routes), label="SYNTHETIC three-supplier finite Nd/Pr/Dy/Tb four-stage network"), suppliers


def synthetic_experiment(draws):
    output = ROOT / "outputs/synthetic/forecast"
    output.mkdir(parents=True, exist_ok=True)
    network, suppliers = synthetic_network()
    origin_quarter = quarter_index("2026Q3")
    quarters = np.arange(origin_quarter + 1, quarter_index("2036Q3") + 1)
    initial_states = ("O", "Q", "C")
    commissioning = (origin_quarter - 8, None, None)
    nominal = {a.id: a.capacity for a in network.activities}
    projects = [ProjectSnapshot(f"{s}_magnet_activity", s, s, "magnet", state, 2,
        date(2026, 9, 30), commission, target_commission_quarter=origin_quarter + i * 4)
        for i, (s, state, commission) in enumerate(zip(suppliers, initial_states, commissioning))]
    ramps = {p.activity_id: RampSpec(4 * nominal[p.activity_id], kind="step") for p in projects}
    balance_residuals, n1_outage_counts = [], {s: 0 for s in suppliers}
    def physical(quarter, capacities, context):
        results = [solve_network(network, [quarter], capacity_overrides=capacities,
            failed_groups={"CHN", supplier}) for supplier in suppliers]
        worst = min(range(len(results)), key=lambda j: results[j].served_fraction_by_quarter[quarter])
        n1_outage_counts[suppliers[worst]] += 1
        balance_residuals.extend(r.diagnostics["max_abs_balance_residual"] for r in results)
        raw = min(sum(cap for activity, cap in capacities.items() if not activity.startswith(s)) / 60
            for s in suppliers)
        result = results[worst]
        return {"served_fraction": result.served_fraction_by_quarter[quarter], "raw_coverage": raw,
            "bottleneck": suppliers[worst] + ":" + ";".join(str(b["variable"]) for b in result.bottlenecks)}
    # Valid because all routes, demand, finite feeds and no-inventory physical
    # assumptions are stationary. Exact unrounded capacity patterns form keys.
    bridge = CachedPhysicalBridge(physical, context_key=lambda q, context: "stationary_network_no_stocks")
    rates = {("C", "Q"): .20, ("C", "X"): .01, ("Q", "O"): .30, ("Q", "X"): .008,
        ("O", "S"): .005, ("S", "O"): .15, ("S", "Q"): .15, ("S", "C"): .15, ("S", "X"): .01}
    model = TransitionModel(rates, provenance="fully_synthetic_engineering_fixture")
    streams = {name: np.random.default_rng(seed) for name, seed in {
        "projects": 202, "common_shocks": 404, "parameters": 101, "process_yields": 303}.items()}
    config = {"origin": "2026-09-30", "quarters": quarters, "physical_bridge": bridge,
        "common_sigma": .30, "group_sigma": .25, "idio_sigma": .10, "common_ar1": .5,
        "provenance": "SYNTHETIC ONLY; no industrial data or empirical hazard estimates"}
    started = time.monotonic()
    panel = simulate_projects(projects, model, ramps, config, streams, draws)
    summaries = summarize_thresholds(panel, [quarter_index(q) for q in ("2028Q4", "2031Q4", "2035Q4")])
    for row in summaries:
        row["target"] = quarter_label(row["target_quarter_index"])
        row["evidence_class"] = "fully_synthetic_engineering_validation"
    quantiles = np.quantile(panel.served_fraction, [.025, .1, .25, .5, .75, .9, .975], axis=0)
    np.savez_compressed(output / "synthetic_draws.npz", quarters=panel.quarters,
        served_fraction=panel.served_fraction, raw_coverage=panel.raw_coverage,
        state_counts=panel.state_counts, quantiles=quantiles)
    write_json(output / "threshold_probabilities.json", summaries)
    # Exercise all five baseline implementations with SYNTHETIC histories only.
    historical_q = np.arange(origin_quarter - 11, origin_quarter + 1)
    historical_y = 1 / (1 + np.exp(-(-2 + .10 * (historical_q - historical_q[0]))))
    baselines = {"zero_new_build": zero_new_build(historical_y[-1], len(quarters)),
        "announced_on_time": announced_on_time(projects, quarters, bridge, ramps),
        "historical_mean_delay": mean_delay_schedule(projects, quarters, bridge, ramps, [1, 2, 3, 4, 5, 6]),
        "linear_trend": linear_trend(historical_q, historical_y, quarters),
        "aggregate_logistic_trend": logistic_trend(historical_q, historical_y, quarters)}
    with (output / "synthetic_baseline_paths.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["quarter", *baselines])
        writer.writerows([quarter_label(q), *(float(x[i]) for x in baselines.values())] for i, q in enumerate(quarters))
    # Separate seeded train/test sample recovers a known quarterly cause rate.
    truth = TransitionModel({("Q", "O"): .25, ("Q", "X"): .08})
    p = truth.probabilities("Q")
    recovery_rng = np.random.default_rng(808)
    training = recovery_rng.choice(list(p), 30000, p=list(p.values())).tolist()
    fit = fit_constant_intensities("Q", ["O", "X"], training)
    test_y = recovery_rng.choice(list(p), 10000, p=list(p.values())) == "O"
    predicted = fit.model.probabilities("Q")["O"]
    recovery = {"evidence_class": "fully_synthetic", "training_n": len(training), "test_n": len(test_y),
        "known_true_rates": {f"{a}->{b}": r for (a,b), r in truth.rates.items()},
        "estimated_rates": {f"{a}->{b}": r for (a,b), r in fit.model.rates.items()},
        "optimizer_success": fit.success,
        "heldout_scores": {"estimated_constant_hazard": binary_scores(predicted, test_y),
            "known_truth": binary_scores(p["O"], test_y), "uninformative_half": binary_scores(.5, test_y),
            "zero_new_build": binary_scores(0, test_y), "certain_on_time": binary_scores(1, test_y)},
        "continuous_score_check": {"samples": [0, 1], "observation": .5,
            "crps": crps_ensemble([0, 1], .5)},
        "interpretation": "Software recovery/score validation only; not historical forecast performance."}
    write_json(output / "parameter_recovery_and_scoring.json", recovery)
    years = panel.quarters / 4
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.fill_between(years, quantiles[0], quantiles[-1], color="#9ecae1", label="95% predictive interval")
    ax.fill_between(years, quantiles[1], quantiles[-2], color="#4292c6", alpha=.7, label="80% predictive interval")
    ax.plot(years, quantiles[3], color="#08306b", label="Median")
    ax.set(xlabel="Year", ylabel="Physically feasible China-free + N−1 service", ylim=(-.03, 1.03),
        title="SYNTHETIC engineering validation — not a real-world forecast")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "synthetic_forecast_service.pdf")
    fig.savefig(output / "synthetic_forecast_service.png", dpi=180)
    plt.close(fig)
    diagnostics = {"evidence_class": "fully_synthetic", "n_independent_draws": draws,
        "quarters": [quarter_label(int(quarters[0])), quarter_label(int(quarters[-1]))],
        "simulation_seconds": time.monotonic() - started,
        "unique_physical_capacity_patterns": bridge.solver_calls,
        "nminus1_solver_calls": len(balance_residuals),
        "max_physical_balance_residual": max(balance_residuals),
        "all_target_mcse_at_most_005": all(row[k]["mc_tolerance_met"] for row in summaries for k in ("start_by_target", "recognized_by_target")),
        "threshold_service_tolerance": 1e-8,
        "uncertainty_included": ["common AR(1) shocks", "supplier-group shocks", "idiosyncratic shocks", "competing project transitions"],
        "uncertainty_excluded": ["estimated parameter posterior", "uncertain engineering recipes", "demand growth", "empirical reporting delays"],
        "physical_conditions": "Finite all-four-stage Nd/Pr/Dy/Tb recipes, finite feedstocks and disposal, no stock carryover; only final-magnet commissioning uncertain; each supplier outage removes its complete chain.",
        "not_empirical": True}
    write_json(output / "diagnostics.json", diagnostics)
    return diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--skip-synthetic", action="store_true")
    args = parser.parse_args()
    readiness = audit_empirical_readiness()
    print(f"Empirical forecasts: {readiness['status']} (no numerical probabilities reported)")
    if not args.skip_synthetic:
        diagnostics = synthetic_experiment(args.draws)
        print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
