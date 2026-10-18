"""All test observations are synthetic fixtures, not Chinese capability data."""

import numpy as np
import pandas as pd
import pytest

from weaponized.semiconductors.access import effective_availability, strict_bottleneck, soft_minimum
from weaponized.semiconductors.capability import LayerParameters, effort_target, fixed_control_steady_state, layer_rhs, simulate_layer
from weaponized.semiconductors.crosswalk import frozen_legal_exposure
from weaponized.semiconductors.evidence import EVIDENCE_COLUMNS, estimate_semiconductor_states
from weaponized.semiconductors.events import forecast_availability, identification_feasibility
from weaponized.semiconductors.legal import LEGAL_COLUMNS, legal_asof, validate_legal_events


def evidence_row(**overrides):
    row = dict(zip(EVIDENCE_COLUMNS, [None] * len(EVIDENCE_COLUMNS)))
    row.update(record_id="SYNTHETIC-record", layer="eda", target_version="SYNTHETIC-target", channel="z", score=.25, lower=.1, upper=.4,
               event_date="2022-01-01", info_public_date="2022-06-01", source_id="SYNTHETIC-source", source_verified=True,
               coder="synthetic-test-coder", confidence="fixture", evidence_memo="SYNTHETIC test fixture")
    row.update(overrides)
    return row


def config(**overrides):
    result = {"as_of": "2022-12-31", "essential_layers": ["eda"], "target_expert_approved": True}
    result.update(overrides)
    return result


def legal_row(**overrides):
    row = dict(zip(LEGAL_COLUMNS, [None] * len(LEGAL_COLUMNS)))
    row.update(policy_id="SYNTHETIC-p", instrument_id="SYNTHETIC-i", version_id="SYNTHETIC-v1", jurisdiction="SYNTHETIC",
               publication_date="2022-01-03", info_public_date="2022-01-01", effective_date="2022-02-01", sha256="a"*64,
               license_requirement="required", status="in_force", source_id="SYNTHETIC-source", evidence_verified=True)
    row.update(overrides)
    return row


def test_separate_channels_and_complementary_sensitivity():
    assert effective_availability(.25, .6) == pytest.approx(.7)
    assert effective_availability(.25, .6, assumption="complementary") == .25
    assert strict_bottleneck([.75, .5, .9]) == .5
    assert np.isnan(strict_bottleneck([.75, np.nan, .9]))
    assert np.isnan(effective_availability(np.nan, .6))
    assert soft_minimum([.5, .5]) == pytest.approx(.5)
    assert strict_bottleneck([.1, .9]) <= soft_minimum([.1, .9]) <= .5
    with pytest.raises(ValueError):
        effective_availability(1.01, .2)


def test_source_cutoff_and_target_mismatch_are_enforced():
    rows = [evidence_row(), evidence_row(record_id="SYNTHETIC-future", score=.9, lower=.8, upper=1, event_date="2022-03-01", info_public_date="2023-01-01")]
    posterior = estimate_semiconductor_states(pd.DataFrame(rows), pd.DataFrame(), "SYNTHETIC-target", config())
    assert posterior.aggregate["domestic_strict_min"] == .25
    mismatch = estimate_semiconductor_states(pd.DataFrame(rows), pd.DataFrame(), "different-target", config())
    assert np.isnan(mismatch.aggregate["domestic_strict_min"])


def test_unapproved_target_and_missing_evidence_never_become_zero():
    result = estimate_semiconductor_states(pd.DataFrame([evidence_row()]), pd.DataFrame(), "SYNTHETIC-target", config(target_expert_approved=False))
    assert np.isnan(result.aggregate["domestic_strict_min"])
    assert result.aggregate["domestic_lower"] == 0
    assert result.aggregate["domestic_upper"] == 1
    assert not result.diagnostics["game_x_available"]


def test_legal_rule_is_not_an_access_observation():
    rows = pd.DataFrame([evidence_row()])
    rules = pd.DataFrame([legal_row(severity_ordinal=1)])
    result = estimate_semiconductor_states(rows, rules, "SYNTHETIC-target", config())
    assert result.layers.z.iloc[0] == .25
    assert np.isnan(result.layers.f.iloc[0])
    assert np.isnan(result.layers.a_residual_gap.iloc[0])


def test_coder_conflict_is_not_averaged():
    rows = pd.DataFrame([evidence_row(), evidence_row(record_id="SYNTHETIC-second", coder="other", score=.35)])
    result = estimate_semiconductor_states(rows, pd.DataFrame(), "SYNTHETIC-target", config())
    assert result.diagnostics["coder_conflicts"] == ["eda:z"]
    assert np.isnan(result.layers.z.iloc[0])


def test_invalid_evidence_bounds_are_rejected():
    with pytest.raises(ValueError, match="bounds"):
        estimate_semiconductor_states(pd.DataFrame([evidence_row(lower=.5, upper=.3)]), pd.DataFrame(), "SYNTHETIC-target", config())


def test_both_legal_clocks_and_future_suspensions():
    initial = legal_row()
    suspension = legal_row(version_id="SYNTHETIC-v2", publication_date="2022-03-01", info_public_date="2022-03-01",
                           effective_date="2022-04-01", status="stayed", supersedes_version="SYNTHETIC-v1")
    frame = pd.DataFrame([initial, suspension])
    assert validate_legal_events(frame)
    assert legal_asof(frame, "2022-01-02").status_asof.tolist() == ["announced_not_effective"]
    assert legal_asof(frame, "2022-02-02").status_asof.tolist() == ["in_force"]
    # A known future suspension does not remove the still-operative original.
    march = legal_asof(frame, "2022-03-15")
    assert set(march.status_asof) == {"in_force", "announced_not_effective"}
    assert legal_asof(frame, "2022-04-01").status_asof.tolist() == ["stayed"]


def test_required_license_is_distinct_from_prohibition():
    frame = pd.DataFrame([legal_row(severity_ordinal=.5, review_presumption="case_by_case")])
    assert validate_legal_events(frame)
    assert frame.license_requirement.iloc[0] == "required"
    with pytest.raises(ValueError):
        validate_legal_events(pd.DataFrame([legal_row(severity_ordinal=.6)]))


def test_frozen_dependency_exposure_ordinal_not_physical():
    data = pd.DataFrame({"jurisdiction": ["SYNTHETIC-US", "SYNTHETIC-JP"], "weight": [.7, .3], "base_year": [2021, 2020],
                         "severity_ordinal": [.75, .5], "source_id": ["SYNTHETIC-a", "SYNTHETIC-b"]})
    assert frozen_legal_exposure(data) == pytest.approx(.675)
    data.loc[0, "base_year"] = 2022
    with pytest.raises(ValueError, match="pre-policy"):
        frozen_legal_exposure(data)


@pytest.mark.parametrize("theta", [-10.0, 0.0, 10.0])
def test_signed_effort_response_nonnegative_and_bounded(theta):
    pars = LayerParameters(kappa=2, g=.01, eta=.15, delta=.08, alpha=-1, theta=theta)
    assert effort_target(1, pars) > 0
    if theta < 0:
        assert effort_target(1, pars) < effort_target(0, pars)
    elif theta > 0:
        assert effort_target(1, pars) > effort_target(0, pars)
    for p in [0.0, .2, 5.0]:
        assert layer_rhs(0, [p, 0], pars, 1)[1] >= 0
        assert layer_rhs(0, [p, 1], pars, 1)[1] <= 0
    solution = simulate_layer(pars, 1, initial=(0, .5), years=25)
    assert np.min(solution.y[0]) >= -1e-10
    assert np.min(solution.y[1]) >= -1e-10
    assert np.max(solution.y[1]) <= 1 + 1e-10
    steady = fixed_control_steady_state(pars, 1)
    assert np.max(np.abs(layer_rhs(0, [steady["p"], steady["z"]], pars, 1))) < 1e-12
    assert max(steady["eigenvalues"]) < 0


def test_degenerate_layer_steady_state_is_continuum_not_zero():
    pars = LayerParameters(kappa=1, g=0, eta=0, delta=0, alpha=1000)
    steady = fixed_control_steady_state(pars, 1)
    assert steady["z"] is None and not steady["unique_z"]
    assert np.isfinite(effort_target(1, pars))


def test_release_lag_and_future_endpoints_block_scoring():
    assert forecast_availability("2022-12-31", 6, "2023-08-01", "SYNTHETIC", "SYNTHETIC")["eligible"]
    assert not forecast_availability("2024-12-31", 24, "2027-02-01", "SYNTHETIC", "SYNTHETIC")["eligible"]
    assert not forecast_availability("2023-12-31", 12, None, "SYNTHETIC", "SYNTHETIC")["eligible"]
    assert not forecast_availability("2023-12-31", 12, "2025-02-01", "SYNTHETIC", "OTHER")["eligible"]


def test_no_causal_claim_without_panel_and_design():
    result = identification_feasibility(pd.DataFrame())
    assert not result["causal_estimation_permitted"]
    assert "no_observed_firm_product_panel" in result["reasons"]
