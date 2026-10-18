from dataclasses import replace
import math
import numpy as np
import pytest
from weaponized.rare_earths.lp import (Activity, Commodity, Demand, ExternalFeed, Facility, Inventory,
                                     Network, ResourceLimit, Route, solve_material_flow, solve_network)
from weaponized.rare_earths.resilience import fixture_ab, fixture_four_elements, make_physical_bridge, nminus1_resilience, raw_capacity_coverage


def test_blueprint_outages_remove_exactly_one_supplier_all_stages():
    net = fixture_ab()
    result = solve_network(net)
    assert result.objective == pytest.approx(1, abs=1e-8)
    assert result.diagnostics["max_abs_balance_residual"] < 1e-8
    assert result.diagnostics["max_dual_stationarity_residual"] < 1e-8
    assert result.diagnostics["primal_dual_gap"] < 1e-8
    assert result.diagnostics["max_complementarity_residual"] < 1e-8
    assert solve_network(net, failed_groups={"A"}).objective == pytest.approx(.5, abs=1e-8)
    assert solve_network(net, failed_groups={"B"}).objective == pytest.approx(4 / 7, abs=1e-8)
    frame = nminus1_resilience(net, initial_exclusions={"CN"}, candidate_suppliers=["A", "B"])
    assert frame.served_fraction.min() == pytest.approx(.5, abs=1e-8)
    assert frame.loc[frame.is_worst_outage, "supplier_removed"].tolist() == ["A"]
    assert raw_capacity_coverage(75, 70) == pytest.approx(15 / 14)
    assert raw_capacity_coverage(75, 70) > result.objective


def test_four_element_native_mass_conservation_and_upstream_cascade():
    net = fixture_four_elements()
    result = solve_network(net)
    assert result.objective == pytest.approx(2 / 3, abs=1e-8)
    assert result.activity["magnet_activity", 0] == pytest.approx(40, abs=1e-6)
    assert result.activity["separation_activity", 0] <= 100
    assert result.diagnostics["max_abs_balance_residual"] < 1e-8
    # Explicit external elemental material equals deliveries plus recovery/disposal loss.
    com = {k.id: k for k in net.commodities}
    for e in ["Nd", "Pr", "Dy", "Tb", "Fe", "B"]:
        supplied = sum(result.external_feed[f.id, 0] * com[f.commodity].elements.get(e, 0) for f in net.feeds)
        delivered = result.delivered["grade_G", 0] * com["magnet"].elements.get(e, 0)
        assert supplied == pytest.approx(delivered + result.diagnostics["contained_element_losses"][str((e, 0))], abs=1e-7)
    no_upstream = solve_network(net, failed_groups={"A"})
    assert no_upstream.objective == 0
    assert no_upstream.activity["magnet_activity", 0] == 0  # B still installed, but A's feed is absent.
    assert solve_network(net, failed_groups={"C"}).objective == 0  # Fe/B is not free.


def _inventory_network():
    return Network((Commodity("mag", "magnet", {"Nd": .3}),), (Facility("bloc"),), (), (), (),
                   (Demand("service", "bloc", {"mag": 1}, 10., 1.),),
                   {("bloc", "mag"): Inventory(10., frozenset({"verified_nonCN"}))},
                   {("bloc", "mag"): 10.}, label="SYNTHETIC stock conservation")


def test_stockpiles_cannot_be_reused_every_quarter():
    result = solve_network(_inventory_network(), [0, 1])
    assert sum(result.delivered.values()) == pytest.approx(10, abs=1e-7)
    assert result.objective == pytest.approx(.5, abs=1e-8)
    assert result.inventory["bloc", "mag", 1] == pytest.approx(0, abs=1e-7)
    with pytest.raises(ValueError, match="consecutive"):
        solve_network(_inventory_network(), [0, 2])


def test_chinese_origin_inventory_removed_but_final_demand_unchanged():
    net = _inventory_network()
    net = replace(net, opening_inventory={("bloc", "mag"): Inventory(10., frozenset({"CN"}))})
    assert solve_network(net).objective == pytest.approx(1, abs=1e-8)
    assert solve_network(net, failed_groups={"CN"}).objective == 0


def test_shipping_disruption_and_shared_resource():
    net = fixture_ab()
    blocked = replace(net, routes=tuple(replace(r, groups=r.groups | {"logistics"}) for r in net.routes))
    assert solve_network(blocked, failed_groups={"logistics"}).objective == 0
    limited = replace(net, resources=(ResourceLimit("shared_magnet_energy", {"magnet_A": 1, "magnet_B": 1}, 28.),))
    assert solve_network(limited).objective == pytest.approx(.4, abs=1e-8)


def test_missing_feed_unknown_capacity_and_invalid_yield_fail_closed():
    net = fixture_ab()
    assert solve_network(replace(net, feeds=())).objective == 0
    with pytest.raises(ValueError, match="finite nonnegative"):
        solve_network(replace(net, feeds=(replace(net.feeds[0], capacity=math.inf),)))
    bad = replace(net.activities[0], inputs={"feed": .5})
    with pytest.raises(ValueError, match="creates contained"):
        solve_network(replace(net, activities=(bad,) + net.activities[1:]))
    with pytest.raises(ValueError, match="Unknown ID"):
        solve_network(net, capacity_overrides={"imaginary": 1000})
    with pytest.raises(ValueError, match="missing quarter"):
        solve_network(replace(net, activities=(replace(net.activities[0], capacity={0: 10.}),) + net.activities[1:]), [1])


def test_policy_access_scales_feeds_without_coding_license_as_ban():
    net = fixture_ab()
    partial = solve_network(net, policy_access={"feed_A": .5, "feed_B": .5})
    assert partial.objective == pytest.approx(52.5 * .9 * .95 / 70, abs=1e-8)
    assert 0 < partial.objective < 1
    with pytest.raises(ValueError):
        solve_network(net, policy_access={"feed_A": 1.1})


def test_joint_multielement_recipe_not_independently_full_nameplate():
    net = fixture_four_elements()
    # A jointly capacity-limited separator: half capacity halves every element output.
    low = solve_network(net, capacity_overrides={"separation_activity": 50.})
    # Tb determines the joint recipe: .002*.75*50 contained Tb, then .95 twice.
    expected = (.002 * .75 * 50 * .95 * .95 / .003) / 60
    assert low.objective == pytest.approx(expected, abs=1e-8)
    assert low.activity["separation_activity", 0] <= 50


def test_origin_erasure_and_contract_adapter():
    net = fixture_ab()
    bad = replace(net, commodities=(replace(net.commodities[0], origin_groups=frozenset({"CN"})),) + net.commodities[1:])
    with pytest.raises(ValueError, match="erases"):
        solve_network(bad)
    assert solve_material_flow(net, quarter=[0]).objective == pytest.approx(1, abs=1e-8)
    with pytest.raises(ValueError, match="Unknown outage"):
        nminus1_resilience(net, candidate_suppliers=["imaginary"])


def test_repeated_solver_and_rescaled_physical_units():
    net = fixture_ab()
    first = solve_network(net)
    second = solve_network(net)
    assert first.activity == second.activity
    scaled = replace(net,
                     activities=tuple(replace(a, capacity=a.capacity * 10000) for a in net.activities),
                     feeds=tuple(replace(f, capacity=f.capacity * 10000) for f in net.feeds),
                     routes=tuple(replace(r, capacity=r.capacity * 10000) for r in net.routes),
                     demands=tuple(replace(d, quantity=d.quantity * 10000) for d in net.demands))
    result = solve_network(scaled)
    assert result.objective == pytest.approx(1, abs=1e-8)
    assert result.diagnostics["max_scaled_balance_residual"] <= 1


def test_weighted_service_reports_essential_grade_shortage_separately():
    net = Network((Commodity("G1", "magnet", {"Nd": .3}), Commodity("G2", "magnet", {"Dy": .03})),
                  (Facility("bloc"),), (), (),
                  (ExternalFeed("G1_feed", "bloc", "G1", 10.), ExternalFeed("G2_feed", "bloc", "G2", 0.)),
                  (Demand("G1_service", "bloc", {"G1": 1.}, 10., .9),
                   Demand("G2_service", "bloc", {"G2": 1.}, 10., .1)))
    result = solve_network(net)
    assert result.objective == pytest.approx(.9, abs=1e-8)
    assert result.min_essential_fraction_by_quarter[0] == 0


def test_stateless_forecast_adapter_rejects_inventory_and_returns_finite_raw_stage_coverage():
    with pytest.raises(ValueError, match="inventories"):
        make_physical_bridge(_inventory_network())
    bridged = make_physical_bridge(fixture_ab())(0, {}, {})
    assert bridged["served_fraction"] == pytest.approx(1, abs=1e-8)
    assert bridged["raw_coverage"] == pytest.approx(75 / 70)
