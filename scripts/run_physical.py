#!/usr/bin/env python3
"""Executed mathematical diagnostics and explicitly SYNTHETIC LP/ODE exhibits."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.integrate import solve_ivp

from weaponized.rare_earths.lp import solve_network
from weaponized.rare_earths.resilience import fixture_ab, fixture_four_elements, nminus1_resilience, raw_capacity_coverage
from weaponized.dynamics import resilience, tipping

OUT = ROOT / "outputs/synthetic/physical"


def serial(value):
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serial(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value)]
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_json(name, value):
    (OUT / name).write_text(json.dumps(serial(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "savefig.dpi": 180, "figure.constrained_layout.use": True})
    ab = fixture_ab()
    ab_results = {label: solve_network(ab, failed_groups=removed) for label, removed in
                  [("A+B", set()), ("Remove A", {"A"}), ("Remove B", {"B"})]}
    n1 = nminus1_resilience(ab, initial_exclusions={"CN"}, candidate_suppliers=["A", "B"])
    n1.to_csv(OUT / "ab_outages.csv", index=False)
    rich = fixture_four_elements()
    cases = {"Installed": solve_network(rich),
             "Half separation": solve_network(rich, capacity_overrides={"separation_activity": 50.}),
             "Half magnets": solve_network(rich, capacity_overrides={"magnet_activity": 20.}),
             "Remove upstream A": solve_network(rich, failed_groups={"A"}),
             "Remove Fe/B supplier C": solve_network(rich, failed_groups={"C"}),
             "50% ore approval": solve_network(rich, policy_access={"ore_feed": .5})}
    write_json("networks.json", {"classification": "SYNTHETIC mathematical fixtures, not empirical networks",
                                "blueprint_ab": asdict(ab), "four_elements": asdict(rich)})
    write_json("flow_results.json", {"classification": "SYNTHETIC; assumed capacities/recipes/ownership/routes",
                                    "ab": {k: asdict(v) for k, v in ab_results.items()},
                                    "four_element_scenarios": {k: asdict(v) for k, v in cases.items()},
                                    "raw_ab_magnet_capacity_coverage": raw_capacity_coverage(75, 70),
                                    "nminus1_ab_service": float(n1.served_fraction.min())})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].bar(list(ab_results), [r.objective for r in ab_results.values()], color=["#23628a", "#b76436", "#b76436"])
    axes[0].set(ylabel="Demand served (fraction)", ylim=(0, 1.1), title="Blueprint A/B network")
    axes[0].axhline(1, color="grey", linestyle=":")
    axes[1].barh(list(cases), [r.objective for r in cases.values()], color="#23628a")
    axes[1].set(xlabel="Demand served (fraction)", xlim=(0, 1), title="Four-element network sensitivities")
    axes[1].invert_yaxis()
    fig.suptitle("SYNTHETIC physical-network verification; no industrial forecast")
    for suffix in ["png", "pdf"]:
        fig.savefig(OUT / f"physical_scenarios.{suffix}")
    plt.close(fig)
    time = np.linspace(0, 20, 401)
    effort_cases = [.1, .6, 1.2]
    eta, delta, initial = .4, .08, .1
    ode_results = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for effort in effort_cases:
        exact = resilience.trajectory(time, initial, eta, effort, delta)
        numeric = solve_ivp(lambda t, r: resilience.rhs(t, r, eta, effort, delta),
                            (0, 20), [initial], t_eval=time, rtol=1e-10, atol=1e-12)
        crossing = resilience.crossing_time(initial, .75, eta, effort, delta)
        ode_results.append({"effort": effort, **resilience.steady_state(eta, effort, delta),
                            "threshold_075_time_years": crossing if np.isfinite(crossing) else None,
                            "crossing_status": "finite" if np.isfinite(crossing) else "not_finitely_reached",
                            "max_numeric_exact_error": float(abs(numeric.y[0] - exact).max())})
        axes[0].plot(time, exact, label=f"I={effort:g}")
    axes[0].axhline(.75, linestyle=":", color="grey", label="Adequacy target 0.75")
    axes[0].set(xlabel="Years", ylabel="Bounded physical proxy r", ylim=(0, 1), title="Adequacy crossing is not a bifurcation")
    axes[0].legend(fontsize=8)
    roots_table = []
    for theta in np.linspace(-3.1, -1.9, 401):
        for root in tipping.fixed_points(float(theta), 5):
            roots_table.append({"theta": float(theta), **asdict(root)})
            stable = root.eigenvalue < 0
            axes[1].plot(theta, root.state, ".", ms=1.7, color="#23628a" if stable else "#b76436")
    folds = tipping.fold_coordinates(5)
    axes[1].scatter([f["theta"] for f in folds], [f["state"] for f in folds], color="black", marker="x", s=25, label="Ordinary folds")
    axes[1].set(xlabel=r"Fundamentals $\theta$", ylabel="Completion propensity z", ylim=(0, 1), title=r"Exploratory logistic feedback, $\beta=5$")
    axes[1].legend(fontsize=8)
    fig.suptitle("SCENARIO mathematics: assumed parameters; no estimated industrial tipping")
    for suffix in ["png", "pdf"]:
        fig.savefig(OUT / f"resilience_bifurcation.{suffix}")
    plt.close(fig)
    write_json("ode_diagnostics.json", {"classification": "SCENARIO mathematical diagnostics; no estimated parameters",
                                       "eta": eta, "delta": delta, "initial": initial, "constant_effort": ode_results,
                                       "zero_rate_case": resilience.steady_state(1, 0, 0),
                                       "folds_beta5": folds, "beta4_theta_minus2": [asdict(r) for r in tipping.fixed_points(-2, 4)],
                                       "roots_beta5_theta_minus2_5": [asdict(r) for r in tipping.fixed_points(-2.5, 5)]})
    pd = __import__("pandas")
    pd.DataFrame(roots_table).to_csv(OUT / "logistic_bifurcation.csv", index=False)
    diag = ROOT / "outputs/diagnostics"
    diag.mkdir(parents=True, exist_ok=True)
    (diag / "physical_readiness.json").write_text(json.dumps({
        "empirical_network_status": "BLOCKED", "empirical_resilience_estimates": None,
        "reason": "No fully evidenced element-specific recipes, routes, ownership, finite feedstock, stocks and grade demand network is registered.",
        "nonlinear_feedback_estimation_status": "BLOCKED",
        "missing_evidence": ["Matched historical project progression and lagged network-density exposures",
                             "Common-shock and endogenous-siting controls", "Sufficient state transitions and out-of-sample outcomes"],
        "implemented": ["multi-commodity multi-quarter LP", "supplier-wide exclusions", "explicit finite feedstocks",
                        "native oxide stoichiometry", "joint recipes", "inventory conservation", "LP dual diagnostics",
                        "bounded resilience exact/numerical ODE", "logistic folds and cubic beta=4 degeneracy"]}, indent=2) + "\n")
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "run_manifest.json")
    write_json("run_manifest.json", {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "research_freeze": "2026-10-11",
                                    "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                                    "classification": "synthetic mathematical verification, not historical evidence",
                                    "input_sha256": {"references/master_blueprint.pdf": hashlib.sha256((ROOT / "references/master_blueprint.pdf").read_bytes()).hexdigest()},
                                    "output_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}})
    print(json.dumps({"ab_service": {k: v.objective for k, v in ab_results.items()}, "four_element_installed": cases["Installed"].objective,
                      "max_ode_error": max(r["max_numeric_exact_error"] for r in ode_results), "output_dir": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
