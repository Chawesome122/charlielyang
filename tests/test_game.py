import numpy as np
import pytest
from scipy.integrate import solve_ivp, quad
from scipy.optimize import minimize_scalar
from weaponized.game.primitives import GameParameters,dynamics,fixed_control_equilibrium,payoffs,pipeline_quarter
from weaponized.game.active_set import solve_stage_nash,conditional_best_responses
from weaponized.game.benchmark import solve_constant_control,constant_control_objective
from weaponized.game.hjb import StateGrid,build_generator,evaluate_policies,piecewise_best_response,own_hamiltonian,policy_deviation_gaps
from weaponized.game.policy_iteration import solve_feedback_game,solve_alternating_game
from weaponized.game.stability import closed_loop_jacobian,feedback_stationary_point
from weaponized.game.calibration import domestic_state,resilience_state,simulate_scalar_transition,fit_scalar_transition


@pytest.mark.parametrize("beta",[-4.,0.,3.])
def test_forward_invariance_and_constant_steady_states(beta):
    p=GameParameters(beta_c=beta,beta_u=-beta)
    rng=np.random.default_rng(491)
    # All boundary faces, arbitrary other coordinates and admissible controls.
    for dim in range(4):
        for endpoint in (0.,1.):
            states=rng.random((100,4));states[:,dim]=endpoint
            f=dynamics(states,rng.random(100),rng.random(100),p)[:,dim]
            assert np.all(f>=-1e-13) if endpoint==0 else np.all(f<=1e-13)
    for _ in range(3):
        u,c=rng.random(2);s0=rng.random(4)
        numerical=solve_ivp(lambda t,s:dynamics(s,u,c,p),(0,200),s0,rtol=1e-10,atol=1e-12,t_eval=np.linspace(0,200,400))
        assert numerical.y.min()>=-1e-9 and numerical.y.max()<=1+1e-9
        steady,eig=fixed_control_equilibrium(u,c,p)
        assert np.max(abs(dynamics(steady,u,c,p)))<1e-14
        assert np.max(abs(numerical.y[:,-1]-steady))<1e-5
        assert np.all(eig<0)


def test_invalid_primitives_and_exact_quarter_time_units():
    with pytest.raises(ValueError):GameParameters(kappa_c=0)
    with pytest.raises(ValueError):GameParameters(k_u=-1)
    assert pipeline_quarter(0,1,4*np.log(2))==pytest.approx(.5)
    assert GameParameters(beta_c=-10,q_c=-.8).beta_c==-10


@pytest.mark.parametrize("ur",[0.,.4,1.])
@pytest.mark.parametrize("cr",[0.,.6,1.])
def test_all_nine_action_regimes(ur,cr):
    mu=ur-.2*cr+(-.3 if ur==0 else .3 if ur==1 else 0)
    mc=cr-.2*ur+(-.3 if cr==0 else .3 if cr==1 else 0)
    found=solve_stage_nash(mu,mc,1,1,.2,.2)
    assert len(found)==1
    assert found[0].u==pytest.approx(ur) and found[0].c==pytest.approx(cr)
    assert found[0].best_response_residual<1e-12


def test_naive_clipping_counterexample_and_singular_continuum():
    solution=solve_stage_nash(1.2,.1,1,1,.8,.8)
    assert len(solution)==1
    assert (solution[0].u,solution[0].c)==pytest.approx((1,.9))
    assert conditional_best_responses(1,1,1.2,.1,1,1,.8,.8)[1]==pytest.approx(.9)
    singular=solve_stage_nash(0,0,1,1,1,1)
    assert any(s.continuum_endpoints==((0.,0.),(1.,1.)) for s in singular)
    # Negative coupling allows multiple isolated equilibria; no uniqueness claim.
    multiple=solve_stage_nash(.5,.5,1,1,-2,-2)
    assert len(multiple)>=3


def test_randomized_active_set_matches_global_br():
    rng=np.random.default_rng(272)
    for _ in range(200):
        mu,mc=rng.normal(size=2);ku,kc=rng.uniform(.1,3,2);qu,qc=rng.uniform(-3,3,2)
        found=solve_stage_nash(mu,mc,ku,kc,qu,qc)
        for candidate in found:
            assert candidate.best_response_residual<1e-9


def test_analytic_self_eroding_benchmark_and_integral():
    result=solve_constant_control()
    assert result["policy"]==pytest.approx(.465571231876768,abs=1e-12)
    assert abs(result["polynomial_residual"])<1e-12
    assert result["policy"]<result["myopic"]
    u=result["policy"]
    objective=quad(lambda t:np.exp(-t)*(u*np.exp(-u*t)-u*u/2),0,np.inf)[0]
    assert objective==pytest.approx(result["objective"],abs=1e-10)
    numerical=minimize_scalar(lambda a:-constant_control_objective(a),bounds=(0,1),method="bounded")
    assert u==pytest.approx(numerical.x,abs=1e-6)


def test_monotone_state_constrained_generator_and_affine_consistency():
    grid=StateGrid(5);p=GameParameters()
    u=np.full(grid.count,.7);c=np.full(grid.count,.2)
    gen=build_generator(grid,p,u,c)
    assert np.max(abs(np.asarray(gen.sum(axis=1))))<1e-13
    assert np.max(gen.diagonal())<=0
    off=gen.copy();off.setdiag(0)
    assert np.min(off.data)>=0
    assert np.allclose(gen@grid.states,dynamics(grid.states,u,c,p),atol=1e-13)


def test_exact_piecewise_response_includes_drift_kink():
    # Deliberately nonconcave kink. A frozen derivative gives a wrong global action.
    pipeline=np.array([.4]);minus=np.array([-2.]);plus=np.array([2.])
    br,value=piecewise_best_response(np.array([.2]),pipeline,np.array([.5]),1,.1,.8,minus,plus)
    actions=np.linspace(0,1,10001)[:,None]
    scores=own_hamiltonian(actions,.2,pipeline,.5,1,.1,.8,minus,plus)
    assert value[0]>=scores.max()-1e-10
    assert br[0]==1


def test_discrete_hjb_candidates_and_unilateral_deviations():
    grid=StateGrid(3)
    result=solve_feedback_game(grid,GameParameters(),starts=("zero","one"),tolerances={"max_iterations":65})
    for run in result["runs"]:
        assert run["status"]=="verified_finite_grid_candidate"
        assert run["continuous_mpe_certified"] is False
        assert run["max_deviation_gain"]<1e-8
        assert run["best_response_action_residual"]<1e-7
        assert max(run["hjb_residuals"])<1e-8
    assert result["runs"][1]["pairwise_policy_sup_distances"]["zero"]<1e-6
    alternate=solve_alternating_game(StateGrid(3),GameParameters(),max_outer=45)
    assert alternate["status"]=="verified_finite_grid_candidate"


def test_closed_loop_jacobian_includes_policy_derivatives():
    p=GameParameters();s=np.array([.5,.5,.5,.5])
    policy=lambda z:(.2+.5*z[0],.3+.4*z[1])
    jac=closed_loop_jacobian(s,policy,p)
    assert jac[2,0]==pytest.approx(p.kappa_c*.5)
    assert jac[3,1]==pytest.approx(p.kappa_u*.4)


def test_stability_at_nonsmooth_policy_knot_is_not_certified():
    grid=StateGrid(5);p=GameParameters(g_c=.1,g_u=.1,delta_c=.1,delta_u=.1,beta_c=0,beta_u=0)
    u=np.clip(.5+2*abs(grid.states[:,2]-.5),0,1);c=np.full(grid.count,.5)
    result=feedback_stationary_point(grid,u,c,p)
    assert result["verified_stationary_point"]
    assert result["stability_status"]=="inconclusive_at_interpolation_knot"
    assert result["locally_stable"] is None


def test_independent_empirical_to_game_measurement_guards():
    assert domestic_state({"litho":.4,"hbm":.2},["litho","hbm"])["state"]==.2
    assert domestic_state({"litho":.4},["litho","hbm"]) is None
    assert resilience_state([5,9],[10,10],[.4,.6])==pytest.approx(.74)
    with pytest.raises(ValueError):resilience_state([75],[70],[1])


def test_synthetic_transition_fit_recovery_and_zero_exposure_nonidentification():
    controls=np.tile([0.,1.,1.,.1,.8,0.],4)
    observed,_=simulate_scalar_transition(controls,.2,0.,.14,.9,.07,.65)
    result=fit_scalar_transition(controls,observed,np.full(25,.01),0.,"synthetic_recovery_test",starts=1)
    assert result["success"] and result["weighted_sse"]<1e-8
    assert result["local_rank"]==4
    assert result["estimates"]["beta"]==pytest.approx(.9,abs=1e-3)
    assert result["estimates"]["kappa"]==pytest.approx(.65,abs=1e-3)
    # With zero control/pipeline, beta and kappa cannot be identified at all.
    observed,_=simulate_scalar_transition(np.zeros(8),.2,0.,.14,.9,.07,.65)
    result=fit_scalar_transition(np.zeros(8),observed,np.full(9,.01),0.,"synthetic_recovery_test",starts=1)
    assert result["local_identification_warning"]
