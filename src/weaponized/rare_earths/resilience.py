"""Physical resilience definitions and explicitly synthetic reference networks."""
from __future__ import annotations

from dataclasses import replace
import math
import pandas as pd

from .lp import (Activity, Commodity, Demand, ExternalFeed, Facility, Network, Route, _at,
                 solve_network)
from .materials import oxide_element_fraction


def raw_capacity_coverage(capacity: float, demand: float) -> float:
    """Uncapped potential at ONE registered stage/product, never across stages."""
    if not math.isfinite(capacity) or capacity < 0 or not math.isfinite(demand) or demand <= 0:
        raise ValueError("Finite nonnegative stage capacity and positive same-basis demand required")
    return capacity / demand


def nminus1_resilience(network: Network, demand=None, initial_exclusions: set[str] | None = None,
                      candidate_suppliers: list[str] | None = None, quarters=(0,)) -> pd.DataFrame:
    """Re-solve one complete outage at a time; importing-bloc demand stays fixed."""
    if demand is not None and tuple(demand) != network.demands:
        network = replace(network, demands=tuple(demand))
    initial = set(initial_exclusions or ())
    candidates = list(candidate_suppliers or ())
    if not candidates or len(set(candidates)) != len(candidates) or initial.intersection(candidates):
        raise ValueError("Register unique extra suppliers disjoint from initial exclusions")
    registered = set().union(*(x.groups for items in (network.facilities, network.activities, network.routes, network.feeds)
                              for x in items), *(k.origin_groups for k in network.commodities),
                             *(inv.groups for inv in network.opening_inventory.values()))
    if set(candidates) - registered:
        raise ValueError("Unknown outage supplier; an absent supplier is not a measured robustness case")
    rows = []
    for supplier in candidates:
        result = solve_network(network, quarters, failed_groups=initial | {supplier})
        for t, fraction in result.served_fraction_by_quarter.items():
            rows.append({"supplier_removed": supplier, "quarter": t, "served_fraction": fraction,
                         "min_essential_fraction": result.min_essential_fraction_by_quarter[t],
                         "exclusions": ";".join(sorted(initial | {supplier})),
                         "max_abs_balance_residual": result.diagnostics["max_abs_balance_residual"]})
    frame = pd.DataFrame(rows)
    frame["is_worst_outage"] = frame.groupby("quarter")["served_fraction"].transform("min").sub(frame.served_fraction).abs() <= 1e-8
    return frame


def fixture_ab() -> Network:
    """Blueprint §3.5 exactly: all values assumptions in contained-NdPr t/q."""
    composition = {"Nd": .75, "Pr": .25}
    commodities = tuple(Commodity(k, form, composition, unit="tonne_contained_element")
                        for k, form in [("feed", "concentrate"), ("oxide", "oxide"),
                                        ("alloy", "alloy"), ("magnet", "magnet")])
    facilities = (Facility("A", frozenset({"A"})), Facility("B", frozenset({"B"})), Facility("bloc"))
    activities = []
    feeds = []
    routes = []
    for supplier, oxide, alloy, magnet in [("A", 60., 50., 40.), ("B", 45., 40., 35.)]:
        group = frozenset({supplier})
        feeds.append(ExternalFeed(f"feed_{supplier}", supplier, "feed", oxide, group))
        activities.extend([Activity(f"separate_{supplier}", supplier, {"feed": 1}, {"oxide": 1}, oxide, group),
                           Activity(f"alloy_{supplier}", supplier, {"oxide": 1 / .9}, {"alloy": 1}, alloy, group),
                           Activity(f"magnet_{supplier}", supplier, {"alloy": 1 / .95}, {"magnet": 1}, magnet, group)])
        routes.append(Route(f"magnet_{supplier}_bloc", supplier, "bloc", "magnet", magnet, group))
    for source, target in [("A", "B"), ("B", "A")]:
        for commodity in ["oxide", "alloy"]:
            routes.append(Route(f"{commodity}_{source}_{target}", source, target, commodity, 105.))
    return Network(commodities, facilities, tuple(activities), tuple(routes), tuple(feeds),
                   (Demand("NdPr_service", "bloc", {"magnet": 1}, 70., 1.),),
                   label="SYNTHETIC blueprint A/B contained-equivalent fixture")


def fixture_four_elements() -> Network:
    """Synthetic four-stage native-mass network; no industrial parameters inferred.

    Explicit finite ore and Fe/B feeds. One shared separation throughput generates
    Nd/Pr/Dy/Tb jointly, with chemically distinct native-mass oxide products.
    A owns upstream ore/mine; B owns separation/alloy/magnet; C supplies Fe/B.
    Removing A starves B even though B's downstream capacity remains installed.
    """
    concentrate = {"Nd": .20, "Pr": .05, "Dy": .01, "Tb": .002}
    alloy = {"Nd": .22, "Pr": .07, "Dy": .015, "Tb": .003, "Fe": .682, "B": .01}
    formula = {"Nd": "Nd2O3", "Pr": "Pr6O11", "Dy": "Dy2O3", "Tb": "Tb4O7"}
    recoveries = {"Nd": .9, "Pr": .85, "Dy": .8, "Tb": .75}
    commodity = [Commodity("ore", "ore", {e: v / 2 for e, v in concentrate.items()}),
                 Commodity("concentrate", "concentrate", concentrate),
                 Commodity("FeB", "other", {"Fe": .682 / .692, "B": .01 / .692}),
                 Commodity("alloy", "alloy", alloy), Commodity("magnet", "qualified_magnet", alloy)]
    for e, ox in formula.items():
        commodity.append(Commodity(ox, "oxide", {e: oxide_element_fraction(ox, e)}))
    oxide_output = {formula[e]: concentrate[e] * recoveries[e] / oxide_element_fraction(formula[e], e)
                    for e in formula}
    alloy_inputs = {formula[e]: alloy[e] / (.95 * oxide_element_fraction(formula[e], e)) for e in formula}
    alloy_inputs["FeB"] = .692
    facilities = (Facility("mine", frozenset({"A", "AUS"})), Facility("separate", frozenset({"B", "USA"})),
                  Facility("alloy", frozenset({"B", "USA"})), Facility("magnet", frozenset({"B", "USA"})), Facility("bloc"))
    activities = (Activity("mine_activity", "mine", {"ore": 2}, {"concentrate": 1}, 100., frozenset({"A"})),
                  Activity("separation_activity", "separate", {"concentrate": 1}, oxide_output, 100., frozenset({"B"})),
                  Activity("alloy_activity", "alloy", alloy_inputs, {"alloy": 1}, 50., frozenset({"B"})),
                  Activity("magnet_activity", "magnet", {"alloy": 1 / .95}, {"magnet": 1}, 40., frozenset({"B"})))
    # Explicit finite discard channels for unsold co-products; no hidden sinks.
    activities += tuple(Activity(f"dispose_{ox}", "separate", {ox: 1}, {}, 100., frozenset({"B"}), "disposal")
                        for ox in formula.values())
    routes = [Route("concentrate_route", "mine", "separate", "concentrate", 100.),
              Route("alloy_route", "alloy", "magnet", "alloy", 50.),
              Route("magnet_route", "magnet", "bloc", "magnet", 40.)]
    routes += [Route(f"route_{ox}", "separate", "alloy", ox, 100.) for ox in formula.values()]
    return Network(tuple(commodity), facilities, activities, tuple(routes),
                   (ExternalFeed("ore_feed", "mine", "ore", 200., frozenset({"A", "AUS"})),
                    ExternalFeed("other_constituents", "alloy", "FeB", 100., frozenset({"C"}))),
                   (Demand("grade_G", "bloc", {"magnet": 1}, 60., 1.),),
                   label="SYNTHETIC four-element native-mass recipe fixture")


def make_physical_bridge(network: Network, *, failed_groups=frozenset(), raw_coverage_function=None):
    """Callable adapter for project Monte Carlo; each call solves a physical LP.

    This STATELESS adapter rejects opening stocks and storage. Inventory-coupled
    forecasts must call solve_network over their joint horizon instead. Default
    raw coverage is defined only for one grade consuming one magnet commodity;
    heterogeneous grades require an explicit registered raw_coverage_function.
    """
    if any(inv.amount > 0 for inv in network.opening_inventory.values()) or network.storage_limits:
        raise ValueError("Stateless physical bridge cannot reuse inventories; solve the joint multi-quarter LP")
    if raw_coverage_function is None and (len(network.demands) != 1 or len(network.demands[0].recipe) != 1):
        raise ValueError("Multiple final grades/products require an explicit registered raw_coverage_function")
    failed = set(failed_groups)
    blocked_nodes = {f.id for f in network.facilities if failed.intersection(f.groups)}

    def bridge(quarter: int, capacities: dict[str, float], draw_context: dict) -> dict:
        result = solve_network(network, [quarter], capacity_overrides=capacities, failed_groups=failed)
        if raw_coverage_function is not None:
            raw = raw_coverage_function(quarter, capacities, draw_context)
        else:
            grade = network.demands[0]
            magnet, per_service = next(iter(grade.recipe.items()))
            available = sum(a.outputs.get(magnet, 0.) * _at(capacities.get(a.id, a.capacity), quarter, a.id)
                            for a in network.activities if a.node not in blocked_nodes and not failed.intersection(a.groups))
            available += sum(_at(f.capacity, quarter, f.id) for f in network.feeds
                             if f.commodity == magnet and f.node not in blocked_nodes and not failed.intersection(f.groups))
            raw = raw_capacity_coverage(available, _at(grade.quantity, quarter, grade.id) * per_service)
        if not math.isfinite(raw) or raw < 0:
            raise ValueError("Registered raw coverage must be finite and nonnegative")
        return {"served_fraction": result.served_fraction_by_quarter[quarter],
                "raw_coverage": float(raw),
                "bottleneck": ";".join(str(b["variable"]) for b in result.bottlenecks),
                "balance_residual": result.diagnostics["max_abs_balance_residual"]}
    return bridge
