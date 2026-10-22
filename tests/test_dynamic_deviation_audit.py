"""Independent discounted-MDP comparisons and original-model special cases."""
import itertools

import numpy as np
import pytest
from scipy import sparse

from weaponized.game.dynamic_deviation_audit import (
    discounted_regret_enclosure, evaluate_fixed_player, solve_fixed_opponent_mdp,
)
from weaponized.game.hjb import StateGrid
from weaponized.game.primitives import GameParameters


def test_two_state_continuous_time_mdp_enclosure_covers_enumerated_exact_optimum():
    rho = .3
    # State-specific rewards and jump rates for two discrete actions.
    rewards = np.array([[.1, .9], [.4, .2]])
    rates = np.array([[.2, .8], [.3, .1]])
    policies = []
    for actions in itertools.product(range(2), repeat=2):
        reward = rewards[np.arange(2), actions]
        rate = rates[np.arange(2), actions]
        gen = np.array([[-rate[0], rate[0]], [rate[1], -rate[1]]])
        value = np.linalg.solve(rho * np.eye(2) - gen, reward)
        policies.append((actions, gen, reward, value))
    optimum = np.max([p[3] for p in policies], axis=0)
    _, generator, reward, exact_base = policies[0]
    base = exact_base + np.array([.002, -.003])
    residual = np.max(abs(rho * base - reward - generator @ base))
    h = rewards + rates * (base[::-1] - base)[:, None]
    gain = np.max(h.max(axis=1) - reward - generator @ base)
    _, devgen, devreward, exact_dev = next(p for p in policies if np.allclose(p[3], optimum))
    deviation = exact_dev + np.array([-.001, .001])
    dev_residual = np.max(abs(rho * deviation - devreward - devgen @ deviation))
    dev_h = rewards + rates * (deviation[::-1] - deviation)[:, None]
    dev_gap = np.max(dev_h.max(axis=1) - devreward - devgen @ deviation)
    bounds = discounted_regret_enclosure(base, residual, max(0, gain), deviation, dev_residual, max(0, dev_gap), rho)
    truth = optimum - exact_base
    assert np.all(bounds['lower_by_state'] <= truth + 1e-12)
    assert np.all(bounds['upper_by_state'] >= truth - 1e-12)
    assert not bounds['floating_point_interval_certified']


def test_discounted_regret_has_exact_inverse_discount_scaling():
    a = discounted_regret_enclosure([0.], .1, .2, [.3], .05, .1, .5)
    b = discounted_regret_enclosure([0.], .1, .2, [.3], .05, .1, 1.)
    assert a['baseline_global_regret_upper_bound'] == 2 * b['baseline_global_regret_upper_bound']


def test_zero_beta_decoupled_mdp_has_exact_myopic_optimal_action_and_frozen_opponent():
    grid = StateGrid(3)
    # With zero beta, q=0 and all other-player flow terms removed, x=0 or1
    # boundaries still do not make x fixed; eliminate own coercion a so that
    # u=0 uniquely maximizes payoff at every state independently of dynamics.
    p = GameParameters(beta_c=0, beta_u=0, a_u=0, q_u=0, d_u=0, h_u=0, b_u=0)
    own = np.full(grid.count, .8)
    opponent = np.linspace(.1, .9, grid.count)
    saved = opponent.copy()
    solution = solve_fixed_opponent_mdp(grid, p, 0, own, opponent, direct=True)
    assert solution['solved_own_mdp']
    assert np.max(abs(solution['own'])) < 1e-10
    assert np.max(abs(solution['value'])) < 1e-10
    assert np.array_equal(opponent, saved)
    assert np.array_equal(solution['fixed_opponent'], saved)
    assert not solution['full_game_nash_verified']


@pytest.mark.parametrize('player', [0, 1])
def test_one_player_sparse_solve_matches_independent_direct_solve(player):
    grid = StateGrid(3); p = GameParameters()
    own = np.linspace(.05, .95, grid.count)
    opponent = np.linspace(.9, .1, grid.count)
    direct, _ = evaluate_fixed_player(grid, p, player, own, opponent, direct=True)
    iterative, diagnostic = evaluate_fixed_player(grid, p, player, own, opponent)
    assert np.max(abs(direct - iterative)) < 1e-9
    assert diagnostic['policy_residual_inf'] < 1e-9


def test_exhausted_budget_returns_value_of_reported_policy_and_reports_failure():
    grid = StateGrid(3); p = GameParameters()
    own = np.full(grid.count, .9); opponent = np.full(grid.count, .3)
    result = solve_fixed_opponent_mdp(grid, p, 0, own, opponent, max_iterations=1, direct=True)
    actual, _ = evaluate_fixed_player(grid, p, 0, result['own'], opponent, direct=True)
    assert not result['solved_own_mdp']
    assert np.max(abs(actual - result['value'])) < 1e-12


@pytest.mark.parametrize('rho,residual', [(0., 0.), (.2, -.1)])
def test_invalid_regret_inputs_rejected(rho, residual):
    with pytest.raises(ValueError):
        discounted_regret_enclosure([0.], residual, 0., [0.], 0., 0., rho)


def test_unbounded_opponent_policy_is_rejected():
    grid = StateGrid(3)
    with pytest.raises(ValueError):
        solve_fixed_opponent_mdp(grid, GameParameters(), 0, np.zeros(grid.count), np.ones(grid.count) * 1.01)


def test_source_array_loader_rejects_corruption_and_nonmatching_axes(tmp_path, monkeypatch):
    import hashlib
    import importlib.util
    import json
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / 'scripts/run_dynamic_deviation_audit.py'
    spec = importlib.util.spec_from_file_location('dynamic_audit_loader_test', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    archive = tmp_path / 'fixture.npz'; diagnostic = tmp_path / 'fixture.json'
    grid = StateGrid(3)
    def save(axis):
        np.savez_compressed(archive, axis=axis, u=np.zeros(grid.count), c=np.zeros(grid.count),
                            value_u=np.zeros(grid.count), value_c=np.zeros(grid.count))
        from dataclasses import asdict
        diagnostic.write_text(json.dumps(dict(archive='fixture.npz', archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                                             grid_size=3, parameters=asdict(GameParameters()), status='fully_synthetic_test_fixture')))
    save(grid.axes[0])
    loaded = module.load_registered_archive(diagnostic)
    assert loaded[2].count == grid.count
    with archive.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='checksum'):
        module.load_registered_archive(diagnostic)
    save(grid.axes[0] + .01)
    with pytest.raises(ValueError, match='axis'):
        module.load_registered_archive(diagnostic)


def test_small_hamiltonian_gap_does_not_hide_failed_linear_evaluation(monkeypatch):
    import weaponized.game.dynamic_deviation_audit as module
    grid = StateGrid(3)
    p = GameParameters(a_u=0, q_u=0, d_u=0, h_u=0, b_u=0)
    def inaccurate(*args, **kwargs):
        return np.ones(grid.count), dict(policy_residual_inf=.2, reward_inf=0.)
    monkeypatch.setattr(module, 'evaluate_fixed_player', inaccurate)
    result = module.solve_fixed_opponent_mdp(grid, p, 0, np.zeros(grid.count),
                                             np.zeros(grid.count), max_iterations=1)
    assert result['optimality_gap_inf'] == 0
    assert not result['policy_evaluation_pass']
    assert not result['solved_own_mdp']
