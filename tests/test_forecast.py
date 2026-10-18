from datetime import date
import numpy as np
import pytest
from weaponized.rare_earths.projects import ProjectEvent, ProjectSnapshot, quarter_index, quarter_label, asof_events
from weaponized.rare_earths.transitions import (TransitionModel, competing_probabilities,
    exact_loglik, right_censored_loglik, interval_endpoint_loglik, first_exit_interval_loglik,
    fit_constant_intensities)
from weaponized.rare_earths.ramps import RampSpec
from weaponized.rare_earths.simulate import simulate_projects, CachedPhysicalBridge
from weaponized.forecast.origins import outcome_eligibility, vintage_rows, run_backtests
from weaponized.forecast.scoring import (binary_scores, crps_ensemble, persistence_times,
    probability_summary, empirical_quantiles_with_infinity, summarize_thresholds, time_dependent_brier)
from weaponized.forecast.calibration import (zero_new_build, historical_mean_delay,
    linear_trend, logistic_trend, cumulative_incidence)
from weaponized.forecast.bootstrap import cluster_bootstrap_indices, two_way_pigeonhole_weights


def streams(seed=5):
    return {name: np.random.default_rng(seed + i) for i, name in enumerate(
        ("projects", "common_shocks", "parameters", "process_yields"))}


def test_competing_risks_sum_and_single_cloglog():
    rng = np.random.default_rng(22)
    for _ in range(100):
        rates = dict(zip(("Q", "S", "X"), rng.uniform(0, 2, 3)))
        p = competing_probabilities(rates)
        assert sum(p.values()) == pytest.approx(1)
        assert p["Q"] / p["S"] == pytest.approx(rates["Q"] / rates["S"])
    p = competing_probabilities({"Q": 0.7})["Q"]
    assert np.log(-np.log(1 - p)) == pytest.approx(np.log(0.7))
    assert competing_probabilities({"Q": 0}) == {"stay": 1, "Q": 0}
    with pytest.raises(ValueError):
        competing_probabilities({"Q": -1})


def test_impossible_transitions_and_absorbing_cancellation():
    with pytest.raises(ValueError):
        TransitionModel({("A", "O"): 1})
    model = TransitionModel({("Q", "O"): 0.3, ("Q", "X"): 0.1})
    assert model.probabilities("X") == {"X": 1}
    assert exact_loglik(model, [("A", "O")]) == -np.inf


def test_loglinear_covariate_and_calendar_country_stage_effects():
    model = TransitionModel({("Q", "O"): .2}, covariate_coefficients={("Q", "O"): {"fid": np.log(2)}},
        calendar_log_offsets={("Q", "O", 8081): np.log(2)},
        country_log_offsets={("Q", "O", "AUS"): np.log(2)},
        stage_log_offsets={("Q", "O", "magnet"): np.log(2)})
    with pytest.raises(ValueError, match="covariate missing"):
        model.probabilities("Q")
    p = model.probabilities("Q", covariates={"fid": 1}, calendar_quarter=8081, country="AUS", stage="magnet")
    assert p["O"] == pytest.approx(1 - np.exp(-3.2))


def test_exact_right_interval_likelihoods():
    model = TransitionModel({("Q", "O"): 0.3, ("Q", "X"): 0.1})
    p = model.probabilities("Q")
    assert exact_loglik(model, [("Q", "Q"), ("Q", "O")]) == pytest.approx(np.log(p["Q"] * p["O"]))
    assert right_censored_loglik(model, "Q", 3, complete_surveillance=True) == pytest.approx(-1.2)
    with pytest.raises(ValueError, match="reporting-delay"):
        right_censored_loglik(model, "Q", 3, complete_surveillance=False)
    expected = sum(p["Q"] ** k * p["O"] for k in range(3))
    assert interval_endpoint_loglik(model, "Q", "O", 3) == pytest.approx(np.log(expected))
    assert first_exit_interval_loglik(model, "Q", "O", 2, 3) == pytest.approx(
        np.log((p["Q"] + p["Q"] ** 2) * p["O"]))


def test_interval_integrates_allowed_intermediate_states():
    model = TransitionModel({("C", "Q"): 1, ("Q", "O"): 1})
    assert interval_endpoint_loglik(model, "C", "O", 1) == -np.inf
    assert interval_endpoint_loglik(model, "C", "O", 2) == pytest.approx(np.log((1 - np.exp(-1)) ** 2))
    with pytest.raises(ValueError, match="age-augmented"):
        interval_endpoint_loglik(TransitionModel({("C", "Q"): 1}, age_slopes={"C": .5}), "C", "Q", 2)


def test_estimation_guard_and_synthetic_parameter_recovery():
    with pytest.raises(ValueError, match="NOT_IDENTIFIABLE"):
        fit_constant_intensities("Q", ["O", "X"], ["Q", "O", "Q", "X"])
    truth = TransitionModel({("Q", "O"): 0.25, ("Q", "X"): 0.08})
    p = truth.probabilities("Q")
    rng = np.random.default_rng(202)
    observations = rng.choice(list(p), 30000, p=list(p.values())).tolist()
    result = fit_constant_intensities("Q", ["O", "X"], observations)
    assert result.success
    assert result.model.rates[("Q", "O")] == pytest.approx(0.25, abs=0.008)
    assert result.model.rates[("Q", "X")] == pytest.approx(0.08, abs=0.006)


def test_ramp_capacity_unit_conversion_and_censoring():
    ramp = RampSpec(annual_capacity=400, utilization=0.8, speed_per_quarter=0.5)
    assert ramp.output_capacity(9, 10) == 0
    assert ramp.output_capacity(10, 10) == 0
    assert ramp.output_capacity(11, 10) == pytest.approx(80 * (1 - np.exp(-0.5)))
    assert ramp.output_capacity(100, 10) <= 80
    assert ramp.output_capacity(100, 10, False) == 0
    assert RampSpec(400, kind="step").output_capacity(10, 10) == 100
    with pytest.raises(ValueError):
        RampSpec(1, capacity_unit="kg/year")
    with pytest.raises(ValueError, match="extrapolation"):
        RampSpec(4, kind="observed", observed_fraction={0: 0.2}).output_capacity(2, 0)


def test_vintage_publication_not_event_date():
    event = ProjectEvent("p", "Q", "O", date(2023, 10, 1), date(2023, 12, 31), date(2024, 3, 1), "s")
    assert asof_events([event], date(2023, 12, 31)) == []
    assert len(asof_events([event], date(2024, 3, 1))) == 1
    assert vintage_rows([{"event_date": "2023-01-01", "info_public_date": "2024-01-01"}], date(2023, 12, 31)) == []
    assert quarter_label(quarter_index("2028Q4")) == "2028Q4"


def test_future_endpoint_and_outcome_release_masks():
    assert outcome_eligibility(date(2020, 12, 31), 6, None)["reason"] == "future_endpoint"
    assert not outcome_eligibility(date(2018, 12, 31), 6, None)["scoreable"]
    assert not outcome_eligibility(date(2018, 12, 31), 6, date(2026, 11, 1))["scoreable"]
    assert outcome_eligibility(date(2018, 12, 31), 6, date(2025, 4, 1))["scoreable"]
    report = run_backtests({}, [(date(2018, 12, 31), 6)], {("2018-12-31", 6): date(2025, 4, 1)}, {}, {})
    assert report[0]["reason"] == "historical_vintage_not_available"


def test_backtests_validate_registered_input_vintages_before_forecast():
    origin = date(2018, 12, 31)
    key = (origin.isoformat(), 2)
    def forbidden():
        raise AssertionError("Leaking forecast must never be invoked")
    registered = {key: {"vintage_id": "snapshot-2018", "prediction_as_of": "2018-12-31",
        "input_info_public_dates": ["2019-01-01"], "prediction": forbidden, "outcome": lambda: 1}}
    report = run_backtests(registered, [(origin, 2)], {key: date(2021, 1, 1)}, {}, {})
    assert report[0]["reason"] == "prediction_vintage_leakage"
    registered[key].update(input_info_public_dates=["2018-12-01"], prediction=lambda: .7)
    report = run_backtests(registered, [(origin, 2)], {key: date(2021, 1, 1)}, {}, {})
    assert report[0]["scoreable"] and report[0]["model"]["brier"] == pytest.approx(.09)


def test_four_quarter_start_recognition_no_crossing_mass():
    y = np.array([[0, .75, .8, .9, 1, 1], [.8, .8, .8, .7, .9, 1]])
    start, recognition = persistence_times(y, np.arange(10, 16), .75)
    assert start[0] == 11 and recognition[0] == 14
    assert np.isinf(start[1]) and np.isinf(recognition[1])
    quantiles = empirical_quantiles_with_infinity(start, [.5, .75])
    assert quantiles["0.5"]["quarter_index"] == 11
    assert quantiles["0.75"]["no_crossing_within_horizon"]


def test_proper_scores_and_mc_accuracy():
    assert binary_scores([0, 1], [0, 1])["negative_log_score"] == 0
    assert binary_scores([1], [0])["negative_log_score"] == np.inf
    assert binary_scores([.2, .8], [0, 1])["brier"] == pytest.approx(.04)
    assert crps_ensemble([0, 1], .5) == .25
    assert crps_ensemble([1, 1], 1) == 0
    summary = probability_summary(np.arange(10000) < 5000)
    assert summary["mc_standard_error"] == .005 and summary["mc_tolerance_met"]
    assert not probability_summary(np.arange(100) < 50)["mc_tolerance_met"]
    assert not probability_summary([False])["mc_tolerance_met"]
    with pytest.raises(ValueError):
        probability_summary([np.nan])


def test_competing_risk_ipcw_brier_and_cif():
    # One commissioning, one cancellation, one still at risk: competing event is
    # an observed zero for commissioning, rather than silently excluded.
    score = time_dependent_brier([.5, .5, .5], [1, 2, 4], [1, 2, 0], 3, 1, lambda t, left: 1)
    assert score["ipcw_brier"] == .25 and score["known_status_n"] == 3
    cif = cumulative_incidence([1, 2, 4], [1, 2, 0], 3)
    assert cif["cumulative_incidence"] == pytest.approx(1 / 3)
    assert cif["event_free_survival"] == pytest.approx(1 / 3)
    with pytest.raises(ValueError, match="inverse weight"):
        time_dependent_brier([.5], [2], [1], 3, 1, lambda t, left: 0)


def test_simulation_requires_physical_bridge_and_preserves_common_shocks():
    projects = [ProjectSnapshot(f"p{i}", f"p{i}", "shared", "magnet", "Q", 0, date(2020, 1, 1)) for i in range(2)]
    ramps = {p.activity_id: RampSpec(4, kind="step") for p in projects}
    model = TransitionModel({("Q", "O"): 0.7})
    config = {"origin": "2020-01-01", "quarters": [8081]}
    with pytest.raises(ValueError, match="bridge"):
        simulate_projects(projects, model, ramps, config, streams(), 2)
    config.update(physical_bridge=lambda q, caps, context: {
        "served_fraction": caps["p1"], "raw_coverage": caps["p0"], "bottleneck": "fixture"},
        group_sigma=2, provenance="synthetic")
    panel = simulate_projects(projects, model, ramps, config, streams(), 2000)
    assert np.corrcoef(panel.served_fraction[:, 0], panel.raw_coverage[:, 0])[0, 1] > .2
    assert panel.state_counts.sum(axis=2).tolist() == [[2000, 2000]]


def test_capacity_cache_and_baselines_and_cluster_weights():
    calls = []
    def physical(q, caps, ctx):
        calls.append(q)
        return {"served_fraction": min(caps.values()), "raw_coverage": 1}
    bridge = CachedPhysicalBridge(physical, context_key=lambda q, context: "stationary")
    bridge(0, {"a": 1}, {})
    bridge(1, {"a": 1}, {})
    assert len(calls) == bridge.solver_calls == 1
    assert np.array_equal(zero_new_build(.3, 3), [.3] * 3)
    assert historical_mean_delay([1, 2, 3, 4, 5]) == 3
    assert linear_trend([1, 2, 3], [.1, .2, .3], [4])[0] == pytest.approx(.4)
    fitted = logistic_trend(np.arange(8), 1 / (1 + np.exp(-(.2 * np.arange(8) - 2))), [8])
    assert fitted[0] == pytest.approx(1 / (1 + np.exp(.4)), abs=1e-5)
    resamples = cluster_bootstrap_indices(["A", "A", "B", "B"], np.random.default_rng(3), 10)
    assert all(len(r) == 4 for r in resamples)
    weights = two_way_pigeonhole_weights(["A", "A", "B", "B"], [1, 2, 1, 2], np.random.default_rng(4), 10)
    assert weights.shape == (10, 4)
