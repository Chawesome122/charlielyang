import math
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from weaponized.dynamics import resilience as r
from weaponized.dynamics import tipping as t


def test_physical_closed_form_and_upward_crossing():
    time = np.linspace(0, 100, 201)
    eta, effort, delta = .4, .8, .08
    exact = r.trajectory(time, .1, eta, effort, delta)
    numeric = solve_ivp(lambda time, state: r.rhs(time, state, eta, effort, delta),
                        (0, 100), [.1], t_eval=time, rtol=1e-10, atol=1e-12)
    assert np.max(np.abs(exact - numeric.y[0])) < 1e-9
    assert r.steady_state(eta, effort, delta)["state"] == pytest.approx(.8)
    crossing = r.crossing_time(.1, .75, eta, effort, delta)
    assert float(r.trajectory(crossing, .1, eta, effort, delta)) == pytest.approx(.75)
    assert math.isinf(r.crossing_time(.1, .8, eta, effort, delta))
    assert math.isinf(r.crossing_time(.1, 1., eta, effort, 0.))
    assert r.critical_effort(.75, eta, delta) == pytest.approx(.6)


def test_no_effort_no_decay_is_neutral_continuum_not_division_by_zero():
    assert r.steady_state(1, 0, 0)["state"] is None
    assert r.steady_state(1, 0, 0)["eigenvalue"] == 0
    assert np.all(r.trajectory([0, 10], .3, 1, 0, 0) == .3)
    assert math.isinf(r.crossing_time(.3, .5, 1, 0, 0))


def test_randomized_forward_invariance_and_boundaries():
    rng = np.random.default_rng(303)
    for _ in range(30):
        eta, effort, delta = rng.uniform(.01, 3), rng.uniform(0, 3), rng.uniform(0, 2)
        assert r.rhs(0, 0, eta, effort, delta) >= 0
        assert r.rhs(0, 1, eta, effort, delta) <= 0
        path = r.trajectory(np.linspace(0, 30, 51), rng.uniform(), eta, effort, delta)
        assert np.all((path >= 0) & (path <= 1))
        theta, beta = rng.uniform(-8, 8), rng.uniform(-8, 8)
        assert t.rhs(0, 0, theta, beta) >= 0
        assert t.rhs(0, 1, theta, beta) <= 0
        numerical = solve_ivp(lambda time, z: t.rhs(time, float(z[0]), theta, beta),
                              (0, 30), [rng.uniform()], rtol=1e-9, atol=1e-11)
        assert numerical.y.min() >= -1e-9 and numerical.y.max() <= 1 + 1e-9


def test_three_logistic_roots_folds_and_stability():
    folds = t.fold_coordinates(5)
    assert folds[0]["state"] == pytest.approx(.27639320225)
    assert folds[1]["state"] == pytest.approx(.72360679775)
    lo, hi = t.three_root_region(5)
    assert lo < -2.5 < hi
    roots = t.fixed_points(-2.5, 5)
    assert len(roots) == 3
    assert [root.stability for root in roots] == ["asymptotically_stable", "unstable", "asymptotically_stable"]
    assert max(abs(root.residual) for root in roots) < 1e-10
    for fold in folds:
        at_fold = t.fixed_points(fold["theta"], 5)
        assert len(at_fold) == 2
        assert any(root.stability == "nonhyperbolic_fold_semistable" for root in at_fold)
        assert abs(fold["second_state_derivative"]) > 0


def test_beta_four_degeneracy_is_cubic_stable_not_two_folds():
    roots = t.fixed_points(-2, 4)
    assert len(roots) == 1
    assert roots[0].state == pytest.approx(.5)
    assert roots[0].stability == "nonhyperbolic_asymptotically_stable_cubic"
    assert t.fold_coordinates(4) == []
    h = 1e-3
    assert t.rhs(0, .5 - h, -2, 4) > 0
    assert t.rhs(0, .5 + h, -2, 4) < 0
    assert t.rhs(0, .5 + h, -2, 4) / h**3 == pytest.approx(-4 / 3, rel=1e-5)


@pytest.mark.parametrize("beta", [-10, 0, 3, 4])
def test_no_three_roots_at_or_below_critical_beta(beta):
    for theta in [-100, -2, 0, 5, 100]:
        roots = t.fixed_points(theta, beta)
        assert len(roots) == 1
        assert abs(roots[0].residual) < 1e-9


def test_invalid_ode_parameters_are_explicit():
    with pytest.raises(ValueError):
        r.trajectory([0], .5, 1, -1, 1)
    with pytest.raises(ValueError):
        t.fixed_points(0, 1, -1)
