"""Correlated project simulation linked to a supplied physical-network solver.

No default capacity-to-service conversion exists: a missing physical bridge is a
hard error. This prevents commissioning nameplate from becoming invented supply.
"""
from dataclasses import dataclass
from datetime import date
from typing import Callable, Mapping
import numpy as np
from .projects import ProjectSnapshot, STATES, validate_snapshot
from .ramps import RampSpec
from .transitions import TransitionModel


@dataclass
class DrawPanel:
    quarters: np.ndarray
    served_fraction: np.ndarray
    raw_coverage: np.ndarray
    bottleneck: np.ndarray
    state_counts: np.ndarray
    activity_ids: list[str]
    provenance: str
    metadata: dict


def simulate_projects(asof_snapshot, transition_model, ramp_model,
                      demand_scenarios, rng_streams, n_draws) -> DrawPanel:
    """Blueprint interface; supplies physical bridge(quarter, capacities, context).

    The bridge must solve registered routing/demand/outage constraints and return
    served_fraction, raw_coverage, bottleneck. Project capacities are in t/q of
    the separately documented activity basis, not summed across process stages.
    `physical_draw` can draw admissible yields/recipes/demand once per path. The
    parameter draw callable, if provided, returns a TransitionModel per path.
    Common and ownership-group Gaussian shocks act on log intensities; quarterly
    AR(1) common shocks are initialized in their stationary distribution.
    """
    origin = demand_scenarios["origin"]
    if isinstance(origin, str):
        origin = date.fromisoformat(origin)
    projects = validate_snapshot(asof_snapshot, origin)
    quarters = np.asarray(demand_scenarios["quarters"], dtype=int)
    if n_draws <= 0 or quarters.size == 0 or np.any(np.diff(quarters) != 1):
        raise ValueError("Require positive draws and consecutive forecast quarters")
    origin_quarter = origin.year * 4 + (origin.month - 1) // 3
    durations = demand_scenarios.get("duration_by_quarter", {})
    if quarters[0] < origin_quarter or (quarters[0] == origin_quarter and int(quarters[0]) not in durations):
        raise ValueError("Start after the origin quarter, or explicitly register its remaining-quarter duration")
    if any(not 0 < duration <= 1 for duration in durations.values()):
        raise ValueError("Quarter duration fractions must be in (0,1]")
    bridge: Callable = demand_scenarios.get("physical_bridge")
    if not callable(bridge):
        raise ValueError("Physical network bridge required; capacity ratios cannot stand in for service")
    if any(p.activity_id not in ramp_model for p in projects):
        raise ValueError("Every activity requires a documented ramp specification")
    for p in projects:
        if p.state == "O" and p.commissioning_quarter is None:
            raise ValueError("Operating activity requires commissioning age or observed-output ramp")
    required_rngs = ("projects", "common_shocks", "parameters", "process_yields")
    if any(k not in rng_streams for k in required_rngs):
        raise ValueError("Supply independent named RNG streams")
    project_rng, common_rng = rng_streams["projects"], rng_streams["common_shocks"]
    common_sigma = float(demand_scenarios.get("common_sigma", 0))
    group_sigma = float(demand_scenarios.get("group_sigma", 0))
    idio_sigma = float(demand_scenarios.get("idio_sigma", 0))
    ar1 = float(demand_scenarios.get("common_ar1", 0))
    if min(common_sigma, group_sigma, idio_sigma) < 0 or abs(ar1) >= 1:
        raise ValueError("Invalid common/idiosyncratic shock specification")
    activity_offsets = demand_scenarios.get("activity_log_offsets", {})
    duration_by_quarter = demand_scenarios.get("duration_by_quarter", {})
    groups = list(dict.fromkeys(p.group_id for p in projects))
    shape = (n_draws, len(quarters))
    served, raw = np.zeros(shape), np.zeros(shape)
    bottleneck = np.empty(shape, dtype=object)
    state_counts = np.zeros((len(quarters), len(projects), len(STATES)), dtype=int)
    parameter_draw = demand_scenarios.get("parameter_draw")
    physical_draw = demand_scenarios.get("physical_draw")
    for draw in range(n_draws):
        model = parameter_draw(rng_streams["parameters"]) if parameter_draw else transition_model
        physical = physical_draw(rng_streams["process_yields"]) if physical_draw else {}
        states = [p.state for p in projects]
        ages = [p.state_age_quarters for p in projects]
        resume = [p.resume_state for p in projects]
        commissioning = [p.commissioning_quarter for p in projects]
        common = common_rng.normal(0, common_sigma)
        for t, quarter in enumerate(quarters):
            if t:
                common = ar1 * common + common_rng.normal(0, common_sigma * np.sqrt(1 - ar1 ** 2))
            group_shock = dict(zip(groups, common_rng.normal(0, group_sigma, len(groups))))
            capacities = {}
            for j, project in enumerate(projects):
                shock = common + group_shock[project.group_id] + project_rng.normal(0, idio_sigma)
                # Centering preserves unconditional rate means for independent Gaussian components.
                shock -= (common_sigma ** 2 + group_sigma ** 2 + idio_sigma ** 2) / 2
                shock += activity_offsets.get(project.activity_id, 0)
                probabilities = model.probabilities(states[j], ages[j], shock, resume[j],
                    duration_by_quarter.get(int(quarter), 1.0), covariates=project.lagged_covariates,
                    calendar_quarter=int(quarter), country=project.country, stage=project.stage)
                destinations = list(probabilities)
                index = int(np.searchsorted(np.cumsum(list(probabilities.values())), project_rng.random(), side="right"))
                destination = destinations[min(index, len(destinations) - 1)]
                if destination != states[j]:
                    if destination == "S":
                        resume[j] = states[j] if states[j] != "A" else "F"
                    if destination == "O" and commissioning[j] is None:
                        commissioning[j] = int(quarter)
                    states[j], ages[j] = destination, 0
                else:
                    ages[j] += 1
                state_counts[t, j, STATES.index(states[j])] += 1
                capacities[project.activity_id] = ramp_model[project.activity_id].output_capacity(
                    int(quarter), commissioning[j], states[j] == "O")
            result = bridge(int(quarter), capacities, {"draw": draw, "physical": physical})
            y = float(result["served_fraction"])
            coverage = float(result["raw_coverage"])
            if not np.isfinite(y) or y < -1e-9 or y > 1 + 1e-9 or not np.isfinite(coverage) or coverage < 0:
                raise ValueError("Physical bridge returned invalid service/coverage")
            served[draw, t], raw[draw, t] = np.clip(y, 0, 1), coverage
            bottleneck[draw, t] = str(result.get("bottleneck", "not reported"))
    return DrawPanel(quarters, served, raw, bottleneck, state_counts,
        [p.activity_id for p in projects], demand_scenarios.get("provenance", "scenario"),
        {"n_draws": n_draws, "independent_equal_weight_draws": True,
         "common_sigma": common_sigma, "group_sigma": group_sigma, "idio_sigma": idio_sigma,
         "common_ar1": ar1, "origin": origin.isoformat(),
         "rate_provenance": transition_model.provenance,
         "warning": "Network/parameter inputs require independent empirical validation"})


class CachedPhysicalBridge:
    """Cache a deterministic stationary network result across repeated capacities.

    Include quarter or physical parameters when they affect demand/routes/yields.
    The caller supplies the complete key; no rounding of actual capacities occurs.
    """
    def __init__(self, bridge, context_key=lambda quarter, context: quarter):
        self.bridge, self.context_key, self.cache = bridge, context_key, {}
        self.solver_calls = 0

    def __call__(self, quarter, capacities, context):
        key = (self.context_key(quarter, context), tuple(sorted(capacities.items())))
        if key not in self.cache:
            self.cache[key] = self.bridge(quarter, capacities, context)
            self.solver_calls += 1
        return self.cache[key]
