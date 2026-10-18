"""Synthetic integration: project uncertainty never invents physical feedstock."""
from datetime import date
import numpy as np
import pytest
from weaponized.rare_earths.projects import ProjectSnapshot
from weaponized.rare_earths.transitions import TransitionModel
from weaponized.rare_earths.ramps import RampSpec
from weaponized.rare_earths.simulate import simulate_projects, CachedPhysicalBridge
from weaponized.rare_earths.lp import solve_network
from weaponized.rare_earths.resilience import fixture_four_elements


def test_project_mc_invokes_four_stage_element_balances():
    network = fixture_four_elements()
    residuals = []
    def physical(quarter, capacities, context):
        result = solve_network(network, [quarter], capacity_overrides=capacities)
        residuals.append(result.diagnostics["max_abs_balance_residual"])
        return {"served_fraction": result.served_fraction_by_quarter[quarter],
            "raw_coverage": capacities["magnet_activity"] / 60, "bottleneck": "synthetic"}
    bridge = CachedPhysicalBridge(physical, context_key=lambda q, context: "stationary")
    project = ProjectSnapshot("magnet_activity", "site", "B", "magnet", "Q", 1, date(2020, 1, 1))
    streams = {name: np.random.default_rng(i) for i, name in enumerate(
        ("projects", "common_shocks", "parameters", "process_yields"))}
    panel = simulate_projects([project], TransitionModel({("Q", "O"): .4}),
        {"magnet_activity": RampSpec(160, kind="step")},
        {"origin": "2020-01-01", "quarters": [8081, 8082], "physical_bridge": bridge,
         "provenance": "synthetic"}, streams, 200)
    assert panel.served_fraction.max() == pytest.approx(2 / 3, abs=1e-8)
    assert panel.served_fraction.min() == 0
    assert max(residuals) < 1e-8 and bridge.solver_calls == 2
    # Even an operating magnet nameplate cannot manufacture its own input.
    no_upstream = solve_network(network, [0], capacity_overrides={"mine_activity": 0, "magnet_activity": 40})
    assert no_upstream.served_fraction_by_quarter[0] == 0
