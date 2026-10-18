"""Conservative multi-commodity, multi-quarter process/transport linear program.

Only registered finite external feeds and opening inventories introduce material.
Every joint process has one throughput variable. All amounts use the native mass
basis of the corresponding commodity; its element vector enforces conservation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping, Sequence

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, vstack, csr_matrix

Capacity = float | Mapping[int, float]


@dataclass(frozen=True)
class Commodity:
    id: str
    form: str
    elements: Mapping[str, float]
    origin_groups: frozenset[str] = frozenset()
    unit: str = "tonne_native"


@dataclass(frozen=True)
class Facility:
    id: str
    groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Activity:
    id: str
    node: str
    inputs: Mapping[str, float]
    outputs: Mapping[str, float]
    capacity: Capacity
    groups: frozenset[str] = frozenset()
    kind: str = "process"


@dataclass(frozen=True)
class Route:
    id: str
    source: str
    target: str
    commodity: str
    capacity: Capacity
    groups: frozenset[str] = frozenset()
    cost: float = 1.0


@dataclass(frozen=True)
class ExternalFeed:
    id: str
    node: str
    commodity: str
    capacity: Capacity
    groups: frozenset[str] = frozenset()
    cost: float = 1.0


@dataclass(frozen=True)
class Demand:
    id: str
    node: str
    recipe: Mapping[str, float]
    quantity: Capacity
    weight: float
    essential: bool = True


@dataclass(frozen=True)
class Inventory:
    amount: float
    groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ResourceLimit:
    id: str
    activity_use: Mapping[str, float]
    capacity: Capacity


@dataclass(frozen=True)
class Network:
    commodities: tuple[Commodity, ...]
    facilities: tuple[Facility, ...]
    activities: tuple[Activity, ...]
    routes: tuple[Route, ...]
    feeds: tuple[ExternalFeed, ...]
    demands: tuple[Demand, ...]
    opening_inventory: Mapping[tuple[str, str], Inventory] = field(default_factory=dict)
    storage_limits: Mapping[tuple[str, str], Capacity] = field(default_factory=dict)
    resources: tuple[ResourceLimit, ...] = ()
    label: str = "unclassified"


@dataclass
class FlowResult:
    success: bool
    objective: float
    served_fraction_by_quarter: dict[int, float]
    min_essential_fraction_by_quarter: dict[int, float]
    delivered: dict[tuple[str, int], float]
    activity: dict[tuple[str, int], float]
    flows: dict[tuple[str, int], float]
    external_feed: dict[tuple[str, int], float]
    inventory: dict[tuple[str, str, int], float]
    balance_residuals: dict[tuple[str, str, int], float]
    bottlenecks: list[dict]
    diagnostics: dict
    failed_groups: tuple[str, ...]


def _number(value: float, label: str) -> float:
    if not isinstance(value, (float, int, np.number)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label}: finite nonnegative value required; unknown is not unlimited")
    return float(value)


def _at(value: Capacity, quarter: int, label: str) -> float:
    if isinstance(value, Mapping):
        if quarter not in value:
            raise ValueError(f"{label}: missing quarter {quarter}")
        return _number(value[quarter], label)
    return _number(value, label)


def validate_network(network: Network, quarters: Sequence[int]) -> None:
    """Reject unknown capacities, elements, impossible recipes and provenance erasure."""
    if not quarters or list(quarters) != sorted(set(quarters)):
        raise ValueError("Quarters must be a strictly increasing nonempty sequence")
    if len(quarters) > 1 and any(b != a + 1 for a, b in zip(quarters[:-1], quarters[1:])):
        raise ValueError("Multi-quarter inventories require consecutive quarters")
    collections = [network.commodities, network.facilities, network.activities, network.routes,
                   network.feeds, network.demands, network.resources]
    for items in collections:
        if len({x.id for x in items}) != len(items):
            raise ValueError("IDs must be unique within each record type")
    if not network.commodities or not network.facilities or not network.demands:
        raise ValueError("Commodities, facilities and final demand required")
    com = {k.id: k for k in network.commodities}
    nodes = {f.id for f in network.facilities}
    activities = {a.id for a in network.activities}
    if abs(sum(d.weight for d in network.demands) - 1) > 1e-10:
        raise ValueError("Frozen grade weights must sum to one")
    for k in com.values():
        if not k.elements or any(_number(v, f"{k.id} composition") > 1 for v in k.elements.values()):
            raise ValueError("A commodity requires explicit element fractions in [0,1]")
        if not 0 < sum(k.elements.values()) <= 1 + 1e-10:
            raise ValueError("Contained-element fractions require a positive mass and cannot sum above one")
        if k.unit not in {"tonne_native", "tonne_contained_element"}:
            raise ValueError("LP mass basis must be explicit tonnes; convert other units explicitly")
    elements = set().union(*(set(k.elements) for k in com.values()))
    for a in network.activities:
        if (a.node not in nodes or not a.inputs or a.kind not in {"process", "disposal"}
                or (a.kind == "process" and not a.outputs) or (a.kind == "disposal" and a.outputs)):
            raise ValueError(f"{a.id}: explicit node, inputs and outputs required; no free upstream production")
        for mapping in (a.inputs, a.outputs):
            for k, coef in mapping.items():
                if k not in com:
                    raise ValueError(f"{a.id}: unknown commodity {k}")
                _number(coef, f"{a.id} coefficient")
        if not any(v > 0 for v in a.inputs.values()) or (a.kind == "process" and not any(v > 0 for v in a.outputs.values())):
            raise ValueError(f"{a.id}: positive physical input and process output coefficients required")
        for e in elements:
            feed = sum(v * com[k].elements.get(e, 0) for k, v in a.inputs.items())
            output = sum(v * com[k].elements.get(e, 0) for k, v in a.outputs.items())
            if output > feed + 1e-10 * max(1, feed):
                raise ValueError(f"{a.id} creates contained {e}: {output} > {feed}")
        for k, coeff in a.outputs.items():
            if coeff == 0:
                continue
            origins = set().union(*(com[j].origin_groups for j, v in a.inputs.items()
                                     if v and set(com[j].elements).intersection(com[k].elements)))
            if not origins.issubset(com[k].origin_groups):
                raise ValueError(f"{a.id}: output erases an input commodity origin")
        for t in quarters:
            _at(a.capacity, t, a.id)
    for r in network.routes:
        if r.source not in nodes or r.target not in nodes or r.commodity not in com:
            raise ValueError(f"{r.id}: unknown route endpoint or commodity")
        _number(r.cost, r.id)
        for t in quarters:
            _at(r.capacity, t, r.id)
    for f in network.feeds:
        if f.node not in nodes or f.commodity not in com:
            raise ValueError(f"{f.id}: unknown feed endpoint or commodity")
        _number(f.cost, f.id)
        for t in quarters:
            _at(f.capacity, t, f.id)
    for d in network.demands:
        if d.node not in nodes or not d.recipe:
            raise ValueError(f"{d.id}: final demand node/recipe required")
        _number(d.weight, d.id)
        for k, v in d.recipe.items():
            if k not in com or com[k].form not in {"magnet", "qualified_magnet"}:
                raise ValueError(f"{d.id}: final service must consume a registered finished magnet")
            if _number(v, d.id) <= 0:
                raise ValueError("Final service recipe coefficients must be positive")
        for t in quarters:
            if _at(d.quantity, t, d.id) <= 0:
                raise ValueError("Zero demand requires a separately registered weighting convention")
    for key, inv in network.opening_inventory.items():
        if key[0] not in nodes or key[1] not in com or not isinstance(inv, Inventory):
            raise ValueError("Opening stock requires a known node/commodity and Inventory with provenance")
        _number(inv.amount, "opening inventory")
    for key, cap in network.storage_limits.items():
        if key[0] not in nodes or key[1] not in com:
            raise ValueError("Unknown storage location/commodity")
        for t in quarters:
            _at(cap, t, "storage capacity")
    for r in network.resources:
        for a, v in r.activity_use.items():
            if a not in activities:
                raise ValueError("Unknown activity in shared resource")
            _number(v, r.id)
        for t in quarters:
            _at(r.capacity, t, r.id)


def solve_network(network: Network, quarters: Sequence[int] = (0,), *, failed_groups: set[str] | None = None,
                  policy_access: Mapping[str, Capacity] | None = None,
                  capacity_overrides: Mapping[str, Capacity] | None = None,
                  primary_tolerance: float = 1e-10, balance_atol: float = 1e-8,
                  balance_rtol: float = 1e-8) -> FlowResult:
    """Optimize mean quarterly weighted service, then imported-input plus routing use.

    Missing edges mean no authorized edge. Unknown edge/capacity values raise an
    error. Opening stocks are consumed only once over the entire joint horizon.
    ``policy_access`` values scale registered feed/route/activity capacities.
    """
    validate_network(network, quarters)
    if not 0 <= primary_tolerance <= 1e-6:
        raise ValueError("Primary objective tolerance must be in [0,1e-6]")
    if balance_atol <= 0 or balance_rtol < 0:
        raise ValueError("Dimensionful balance tolerances must be nonnegative with positive absolute tolerance")
    failed = set(failed_groups or ())
    access = policy_access or {}
    overrides = capacity_overrides or {}
    valid_ids = {x.id for xs in (network.activities, network.routes, network.feeds) for x in xs}
    if set(access) - valid_ids or set(overrides) - {a.id for a in network.activities}:
        raise ValueError("Unknown ID in policy access or activity capacity override")
    facility = {f.id: f for f in network.facilities}
    commodity = {k.id: k for k in network.commodities}
    blocked_nodes = {f.id for f in network.facilities if failed.intersection(f.groups)}
    blocked_commodities = {k.id for k in network.commodities if failed.intersection(k.origin_groups)}
    keys: list[tuple] = []
    bounds: list[tuple[float, float]] = []
    primary: list[float] = []
    secondary: list[float] = []

    def add(key: tuple, ub: float, p: float = 0., c: float = 0.):
        keys.append(key); bounds.append((0., ub)); primary.append(p); secondary.append(c)

    def cap(item, t, inactive=False):
        factor = _at(access.get(item.id, 1.), t, f"policy access {item.id}")
        if factor > 1:
            raise ValueError("Policy access fractions must be in [0,1]")
        base = _at(overrides.get(item.id, item.capacity), t, item.id)
        return 0. if inactive or failed.intersection(item.groups) else base * factor

    for t in quarters:
        for a in network.activities:
            inactive = a.node in blocked_nodes or blocked_commodities.intersection(set(a.inputs) | set(a.outputs))
            add(("q", a.id, t), cap(a, t, inactive))
        for r in network.routes:
            add(("f", r.id, t), cap(r, t, r.source in blocked_nodes or r.target in blocked_nodes
                                    or r.commodity in blocked_commodities), c=r.cost)
        for f in network.feeds:
            add(("m", f.id, t), cap(f, t, f.node in blocked_nodes or f.commodity in blocked_commodities), c=f.cost)
        for node in facility:
            for k in commodity:
                ub = _at(network.storage_limits.get((node, k), 0.), t, "storage")
                add(("z", node, k, t), 0. if node in blocked_nodes or k in blocked_commodities else ub)
        for d in network.demands:
            amount = _at(d.quantity, t, d.id)
            add(("d", d.id, t), amount, p=d.weight / amount / len(quarters))
    idx = {key: i for i, key in enumerate(keys)}
    rows = [(node, k, t) for t in quarters for node in facility for k in commodity]
    ridx = {key: i for i, key in enumerate(rows)}
    aeq = lil_matrix((len(rows), len(keys)))
    beq = np.zeros(len(rows))
    for pos, t in enumerate(quarters):
        for node in facility:
            for k in commodity:
                row = ridx[node, k, t]
                aeq[row, idx["z", node, k, t]] = 1.
                if pos:
                    aeq[row, idx["z", node, k, quarters[pos - 1]]] = -1.
                else:
                    inv = network.opening_inventory.get((node, k), Inventory(0.))
                    beq[row] = 0. if (node in blocked_nodes or k in blocked_commodities
                                              or failed.intersection(inv.groups)) else inv.amount
        for a in network.activities:
            for k in set(a.inputs) | set(a.outputs):
                aeq[ridx[a.node, k, t], idx["q", a.id, t]] += a.inputs.get(k, 0.) - a.outputs.get(k, 0.)
        for r in network.routes:
            aeq[ridx[r.source, r.commodity, t], idx["f", r.id, t]] += 1.
            aeq[ridx[r.target, r.commodity, t], idx["f", r.id, t]] -= 1.
        for f in network.feeds:
            aeq[ridx[f.node, f.commodity, t], idx["m", f.id, t]] -= 1.
        for d in network.demands:
            for k, v in d.recipe.items():
                aeq[ridx[d.node, k, t], idx["d", d.id, t]] += v
    resource_rows = [(r, t) for t in quarters for r in network.resources]
    aub = lil_matrix((len(resource_rows), len(keys)))
    bub = []
    for i, (r, t) in enumerate(resource_rows):
        for activity, use in r.activity_use.items():
            aub[i, idx["q", activity, t]] = use
        bub.append(_at(r.capacity, t, r.id))
    aeq, aub = aeq.tocsr(), aub.tocsr()
    p = np.asarray(primary)
    opts = {"dual_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9}
    first = linprog(-p, A_ub=aub if resource_rows else None, b_ub=bub if resource_rows else None,
                    A_eq=aeq, b_eq=beq, bounds=bounds, method="highs", options=opts)
    if not first.success:
        raise RuntimeError(f"Material LP failed ({first.status}): {first.message}; no feed was inserted")
    optimum = float(p @ first.x)
    # Primary value retained to the declared dimensionless service tolerance.
    lex_a = vstack([aub, csr_matrix(-p.reshape(1, -1))], format="csr")
    second = linprog(np.asarray(secondary), A_ub=lex_a, b_ub=np.r_[bub, -optimum + primary_tolerance],
                     A_eq=aeq, b_eq=beq, bounds=bounds, method="highs", options=opts)
    if not second.success:
        raise RuntimeError(f"Secondary lexicographic solve failed: {second.message}")
    x = second.x
    residual = aeq @ x - beq
    scale = np.maximum(1., np.asarray(abs(aeq) @ abs(x)).ravel() + abs(beq))
    scaled = abs(residual) / (balance_atol + balance_rtol * scale)
    bound_violation = max((max(lo - value, value - hi, 0.) for value, (lo, hi) in zip(x, bounds)), default=0.)
    resource_violation = max(np.asarray(aub @ x - np.asarray(bub)).max(initial=0.), 0.)
    if scaled.max(initial=0.) > 1 or bound_violation > balance_atol or resource_violation > balance_atol:
        raise RuntimeError("Material LP returned a solution outside conservation/capacity tolerance")
    activity = {(a.id, t): float(x[idx["q", a.id, t]]) for t in quarters for a in network.activities}
    delivered = {(d.id, t): float(x[idx["d", d.id, t]]) for t in quarters for d in network.demands}
    fractions = {t: sum(d.weight * delivered[d.id, t] / _at(d.quantity, t, d.id)
                        for d in network.demands) for t in quarters}
    min_grade = {t: min((delivered[d.id, t] / _at(d.quantity, t, d.id) for d in network.demands if d.essential),
                       default=float("nan")) for t in quarters}
    bottlenecks = []
    for i, key in enumerate(keys):
        # The primary solve's duals answer marginal service, rather than shipping minimization.
        dual = -float(first.upper.marginals[i])
        if bounds[i][1] > 0 and abs(first.x[i] - bounds[i][1]) <= balance_atol and dual > 1e-10:
            bottlenecks.append({"variable": list(key), "capacity": bounds[i][1], "marginal_service": dual})
    kkt_stationarity = (np.asarray(first.c if hasattr(first, "c") else -p)
                        - np.asarray(aeq.T @ first.eqlin.marginals).ravel()
                        - (np.asarray(aub.T @ first.ineqlin.marginals).ravel() if resource_rows else 0.)
                        - first.lower.marginals - first.upper.marginals)
    lower = np.asarray([b[0] for b in bounds]); upper = np.asarray([b[1] for b in bounds])
    dual_objective = float(beq @ first.eqlin.marginals + lower @ first.lower.marginals + upper @ first.upper.marginals
                           + (np.asarray(bub) @ first.ineqlin.marginals if resource_rows else 0.))
    complementarity = [abs((first.x - lower) * first.lower.marginals).max(initial=0.),
                       abs((upper - first.x) * first.upper.marginals).max(initial=0.)]
    if resource_rows:
        complementarity.append(abs((np.asarray(bub) - aub @ first.x) * first.ineqlin.marginals).max(initial=0.))
    diagnostics = {"solver": "scipy.optimize.linprog/highs", "network_label": network.label,
                   "n_variables": len(keys), "n_balances": len(rows), "primary_optimum": optimum,
                   "secondary_objective": float(second.fun), "primary_loss": optimum - float(p @ x),
                   "max_abs_balance_residual": float(abs(residual).max(initial=0.)),
                   "max_scaled_balance_residual": float(scaled.max(initial=0.)),
                   "max_bound_violation": float(bound_violation), "max_resource_violation": float(resource_violation),
                   "max_dual_stationarity_residual": float(abs(kkt_stationarity).max(initial=0.)),
                   "primal_dual_gap": float(abs(float(first.fun) - dual_objective)),
                   "max_complementarity_residual": float(max(complementarity)),
                   "primary_solver_status": int(first.status), "secondary_solver_status": int(second.status),
                   "primary_equality_duals": {str(key): float(first.eqlin.marginals[i]) for i, key in enumerate(rows)},
                   "contained_element_losses": {
                       str((e, t)): sum(activity[a.id, t] * (
                           sum(v * commodity[k].elements.get(e, 0.) for k, v in a.inputs.items())
                           - sum(v * commodity[k].elements.get(e, 0.) for k, v in a.outputs.items()))
                           for a in network.activities)
                       for t in quarters for e in set().union(*(set(k.elements) for k in network.commodities))},
                   "integrity_flags": {"conservation": True, "finite_registered_feeds": True,
                                       "element_recipe_validation": True, "joint_process_capacity": True,
                                       "stock_not_reused": True}}
    return FlowResult(True, float(p @ x), fractions, min_grade, delivered, activity,
                      {(r.id, t): float(x[idx["f", r.id, t]]) for t in quarters for r in network.routes},
                      {(f.id, t): float(x[idx["m", f.id, t]]) for t in quarters for f in network.feeds},
                      {(node, k, t): float(x[idx["z", node, k, t]]) for t in quarters for node in facility for k in commodity},
                      {row: float(residual[i]) for i, row in enumerate(rows)}, bottlenecks, diagnostics, tuple(sorted(failed)))


def solve_material_flow(facilities, activities=None, input_output_coefficients=None, routes=None, demand=None,
                        initial_inventories=None, policy_access=None, failed_groups=None, quarter=0,
                        solver_config=None) -> FlowResult:
    """Blueprint contract adapter; prefer passing a validated ``Network``.

    For column-oriented data use an explicit conversion to Network rather than
    guessing commodity bases. ``input_output_coefficients`` must contain registered
    ``commodities`` and ``feeds``; activities already contain their vector recipes.
    """
    if isinstance(facilities, Network):
        network = facilities
    else:
        if not isinstance(input_output_coefficients, Mapping):
            raise ValueError("Register commodity compositions and finite feeds in input_output_coefficients")
        network = Network(tuple(input_output_coefficients["commodities"]), tuple(facilities), tuple(activities or ()),
                          tuple(routes or ()), tuple(input_output_coefficients["feeds"]), tuple(demand or ()),
                          initial_inventories or {}, input_output_coefficients.get("storage_limits", {}),
                          tuple(input_output_coefficients.get("resources", ())))
    quarters = [quarter] if isinstance(quarter, (int, np.integer)) else quarter
    return solve_network(network, quarters, policy_access=policy_access, failed_groups=failed_groups, **(solver_config or {}))
