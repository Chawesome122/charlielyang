"""Analytical, variational and original-payoff checks for constant commitments."""
import numpy as np
import pytest

from weaponized.game.active_set import solve_stage_nash
from weaponized.game.constant_controls import (
    constant_path_payoffs, curvature_certificate, discounted_vulnerability,
    private_constant_objectives, solve_constant_path_nash,
)
from weaponized.game.primitives import GameParameters


def exact_zero_beta_vulnerability(initial,g,delta,rho):
    steady=g/(g+delta)
    return (1-steady)/rho+(steady-initial)/(rho+g+delta)


def test_zero_beta_integral_and_tail_against_analytic_solution():
    expected=exact_zero_beta_vulnerability(.25,.12,.08,.2)
    result=discounted_vulnerability(.6,.25,.3,.12,0,.08,.5,.2,horizon=80)
    assert abs(expected-result['value'])<=result['value_tail_bound']+1e-9
    assert result['first']==0 and result['second']==0


@pytest.mark.parametrize('beta',[-.7,.7])
def test_sensitivities_against_independent_control_perturbations(beta):
    def value(u):return discounted_vulnerability(u,.25,0,.12,beta,.08,.5,.2)
    center=value(.45);h=1e-3;lo=value(.45-h);hi=value(.45+h)
    assert abs(center['first']-(hi['value']-lo['value'])/(2*h))<2e-6
    assert abs(center['second']-(hi['value']-2*center['value']+lo['value'])/h**2)<2e-5


def test_zero_beta_reciprocal_solution_matches_exact_constrained_stage_system():
    p=GameParameters(beta_c=0,beta_u=0,rho_c=.3)
    wu=exact_zero_beta_vulnerability(.25,p.g_c,p.delta_c,p.rho_u)
    wc=exact_zero_beta_vulnerability(.25,p.g_u,p.delta_u,p.rho_c)
    exact=solve_stage_nash(p.rho_u*p.a_u*wu,p.rho_c*p.a_c*wc,p.k_u,p.k_c,p.q_u,p.q_c)[0]
    result=solve_constant_path_nash(p,[.25,.25,.2,.4])
    assert result['multiple_start_action_spread']<1e-8
    assert all(max(abs(x['u']-exact.u),abs(x['c']-exact.c))<1e-8 for x in result['runs'])
    assert not result['continuous_feedback_mpe_certified']


def test_constant_game_corner_is_not_independent_clipping():
    wu=exact_zero_beta_vulnerability(.25,.12,.08,.2)
    wc=exact_zero_beta_vulnerability(.25,.1,.07,.2)
    p=GameParameters(beta_c=0,beta_u=0,a_u=2/(.2*wu),a_c=.4/(.2*wc),q_u=.5,q_c=.5)
    result=solve_constant_path_nash(p,[.25,.25,0,0],starts=(.5,))['runs'][0]
    assert abs(result['u']-1)<1e-10 and abs(result['c']-.9)<1e-8


@pytest.mark.parametrize('beta',[-.7,.7])
def test_derived_global_curvature_bound_dominates_computed_curvatures(beta):
    p=GameParameters(beta_c=beta,beta_u=beta);bound=curvature_certificate(p)
    objective=private_constant_objectives(p,[.25,.25,0,0])
    assert bound['certified'] and bound['br_composition_contraction_bound']<1
    for player in [0,1]:
        for control in np.linspace(0,1,5):
            assert objective(player,float(control),.5)['second']<=-bound['players'][player]['strong_concavity_lower_bound']+1e-8


def test_unavailable_contraction_certificate_is_not_an_equilibrium_claim():
    p=GameParameters(q_u=10,q_c=10)
    assert not curvature_certificate(p)['certified']
    with pytest.raises(ValueError,match='do not infer nonexistence'):
        solve_constant_path_nash(p,[.25,.25,0,0])


def test_unbounded_initial_state_is_rejected():
    with pytest.raises(ValueError,match='unit cube'):
        private_constant_objectives(GameParameters(),[1.1,.25,0,0])


def test_private_deviation_objective_agrees_with_original_full_four_state_payoffs():
    p=GameParameters();s=[.25,.25,0,0]
    private=private_constant_objectives(p,s)
    reference=constant_path_payoffs(p,s,.4,.5)['values']
    for player in [0,1]:
        controls=[.4,.5];controls[player]=.7
        changed=constant_path_payoffs(p,s,*controls)['values']
        old_control=[.4,.5][player];other=[.5,.4][player]
        predicted=private(player,.7,other)['value']-private(player,old_control,other)['value']
        assert abs((changed[player]-reference[player])-predicted)<1e-8
