"""Reciprocal Nash benchmark restricted to two constants committed at time zero.

Uses the original four-state dynamics/payoffs. This is neither a feedback MPE
nor an unrestricted open-loop equilibrium. Parameters/initial states are scenarios.
"""
from functools import lru_cache
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from .primitives import dynamics, payoffs


def curvature_certificate(p):
    """Global sufficient concavity bounds and BR-composition contraction.

    If S bounds integral exp(-rho*t)|dx/du| and R bounds the second
    sensitivity integral, the private payoff curvature is at most
    a*(R + 2*S*1{beta<0}) - k/rho. These bounds are uniform over constants
    and all initial states in the unit cube; they are not empirical estimates.
    """
    players=[]
    for g,beta,delta,rho,a,k,q in [
        (p.g_c,p.beta_c,p.delta_c,p.rho_u,p.a_u,p.k_u,p.q_u),
        (p.g_u,p.beta_u,p.delta_u,p.rho_c,p.a_c,p.k_c,p.q_c),
    ]:
        low=g*math.exp(min(0,beta));high=g*math.exp(max(0,beta))
        lam=low+delta;denominator=rho+lam
        first=high*abs(beta)/(rho*denominator)
        second=high*beta*beta/(rho*denominator)+2*high*abs(beta)*first/denominator
        margin=k/rho-a*(second+(2*first if beta<0 else 0))
        lipschitz=abs(q)/(rho*margin) if margin>0 else math.inf
        players.append(dict(discounted_first_sensitivity_bound=first,discounted_second_sensitivity_bound=second,
                            strong_concavity_lower_bound=margin,best_response_lipschitz_bound=lipschitz))
    product=players[0]['best_response_lipschitz_bound']*players[1]['best_response_lipschitz_bound']
    return dict(certified=all(x['strong_concavity_lower_bound']>0 for x in players) and product<1,
                players=players,br_composition_contraction_bound=product,
                scope='Unique Nash within commitment to constant controls at a fixed initial state; no full dynamic equilibrium implication')


def discounted_vulnerability(control, initial, initial_pipeline, g, beta, delta, kappa, rho,
                              horizon=160.,rtol=1e-10,atol=1e-12):
    """Discounted vulnerability and two control sensitivities, with tail bounds."""
    values=[control,initial,initial_pipeline,g,beta,delta,kappa,rho,horizon,rtol,atol]
    if not np.isfinite(values).all() or not all(0<=x<=1 for x in [control,initial,initial_pipeline]) or min(g,kappa,rho,horizon,rtol,atol)<=0 or delta<0:
        raise ValueError('Finite bounded states/control and positive integration primitives required')
    def field(t,z):
        x,s,r=z[:3]
        response=-math.expm1(-kappa*t)
        pipeline=control+(initial_pipeline-control)*math.exp(-kappa*t)
        growth=g*math.exp(beta*pipeline);rate=growth+delta
        forcing=growth*beta*response
        discount=math.exp(-rho*t)
        return [growth*(1-x)-delta*x,forcing*(1-x)-rate*s,
                growth*beta*beta*response*response*(1-x)-2*forcing*s-rate*r,
                discount*(1-x),-discount*s,-discount*r]
    result=solve_ivp(field,(0,horizon),[initial,0,0,0,0,0],method='DOP853',rtol=rtol,atol=atol,max_step=2.)
    if not result.success or result.y[0].min()<-1e-9 or result.y[0].max()>1+1e-9:
        raise RuntimeError('Sensitivity integration failed or left the invariant state interval')
    high=g*math.exp(max(0,beta));lam=g*math.exp(min(0,beta))+delta
    uniform_first=high*abs(beta)/lam
    uniform_second=(high*beta*beta+2*high*abs(beta)*uniform_first)/lam
    tail=math.exp(-rho*horizon)/rho
    return dict(value=float(result.y[3,-1]),first=float(result.y[4,-1]),second=float(result.y[5,-1]),
                value_tail_bound=tail,first_tail_bound=tail*uniform_first,second_tail_bound=tail*uniform_second,
                horizon_years=horizon,numerical_integration_is_interval_certified=False)


def private_constant_objectives(p,state0,horizon=160.,rtol=1e-10,atol=1e-12):
    state0=np.asarray(state0,dtype=float)
    if state0.shape!=(4,) or not np.isfinite(state0).all() or np.any((state0<0)|(state0>1)):
        raise ValueError('A fixed initial state in the four-dimensional unit cube is required')
    @lru_cache(maxsize=8192)
    def vulnerability(player,control):
        args=(state0[0],state0[2],p.g_c,p.beta_c,p.delta_c,p.kappa_c,p.rho_u) if player==0 else (state0[1],state0[3],p.g_u,p.beta_u,p.delta_u,p.kappa_u,p.rho_c)
        return discounted_vulnerability(control,*args,horizon=horizon,rtol=rtol,atol=atol)
    def objective(player,control,other):
        if player not in {0,1} or not math.isfinite(other) or not 0<=other<=1:
            raise ValueError('Registered player and bounded opponent control required')
        a,k,q,rho=(p.a_u,p.k_u,p.q_u,p.rho_u) if player==0 else (p.a_c,p.k_c,p.q_c,p.rho_c)
        w=vulnerability(player,float(control))
        return dict(value=a*control*w['value']-.5*k*control*control/rho+q*control*other/rho,
                    first=a*(w['value']+control*w['first'])-k*control/rho+q*other/rho,
                    second=a*(2*w['first']+control*w['second'])-k/rho,
                    value_tail_bound=a*control*w['value_tail_bound'],
                    gradient_tail_bound=a*(w['value_tail_bound']+control*w['first_tail_bound']))
    return objective


def constant_path_payoffs(p,state0,u,c,horizon=160.,rtol=1e-10,atol=1e-12):
    if not all(0<=x<=1 for x in [u,c]):raise ValueError('Constant controls must lie in [0,1]')
    if not np.isfinite([horizon,rtol,atol]).all() or min(horizon,rtol,atol)<=0:
        raise ValueError('Positive finite integration settings required')
    state0=np.asarray(state0,dtype=float)
    if state0.shape!=(4,) or not np.isfinite(state0).all() or np.any((state0<0)|(state0>1)):
        raise ValueError('Fixed initial state outside unit cube')
    def field(t,z):
        reward=payoffs(z[:4],u,c,p)
        return np.r_[dynamics(z[:4],u,c,p),np.exp(-np.array([p.rho_u,p.rho_c])*t)*reward]
    result=solve_ivp(field,(0,horizon),np.r_[state0,0.,0.],method='DOP853',rtol=rtol,atol=atol,max_step=2.)
    if not result.success or result.y[:4].min()<-1e-9 or result.y[:4].max()>1+1e-9:
        raise RuntimeError('Full original-game payoff integration failed')
    bounds=[p.a_u+p.d_u+.5*p.k_u+.5*p.h_u+p.b_u+abs(p.q_u),p.a_c+p.d_c+.5*p.k_c+.5*p.h_c+p.b_c+abs(p.q_c)]
    return dict(values=result.y[4:,-1].tolist(),tail_absolute_bounds=[b*math.exp(-rho*horizon)/rho for b,rho in zip(bounds,[p.rho_u,p.rho_c])],
                horizon_years=horizon,scope='Original-game payoffs of committed constant paths; finite integration plus analytic omitted-tail bounds')


def solve_constant_path_nash(p,state0,starts=(0.,.5,1.),horizon=160.,action_tolerance=1e-10,max_iterations=100):
    if not starts or not math.isfinite(action_tolerance) or action_tolerance<=0 or max_iterations<=0:
        raise ValueError('Nonempty starts and positive convergence settings required')
    certificate=curvature_certificate(p)
    if not certificate['certified']:
        raise ValueError('Sufficient curvature/contraction certificate unavailable; do not infer nonexistence')
    objective=private_constant_objectives(p,state0,horizon)
    def best(player,other):
        derivative=lambda x:objective(player,float(x),float(other))['first']
        if derivative(0)<=0:return 0.
        if derivative(1)>=0:return 1.
        return float(brentq(derivative,0,1,xtol=1e-12,rtol=1e-12))
    results=[]
    contraction=certificate['br_composition_contraction_bound']
    for start in starts:
        if not 0<=start<=1:raise ValueError('Initial constant action outside [0,1]')
        c=float(start)
        for iteration in range(max_iterations):
            u=best(0,c);new_c=best(1,u);change=abs(new_c-c);c=new_c
            if change/(1-contraction)<=action_tolerance:break
        u=best(0,c)
        residual=max(abs(best(0,c)-u),abs(best(1,u)-c))
        if residual>action_tolerance:raise RuntimeError('Constant-path best-response iteration did not converge')
        results.append(dict(initial_china_action=start,u=u,c=c,iterations=iteration+1,best_response_action_residual=residual))
    spread=max(max(abs(x['u']-results[0]['u']),abs(x['c']-results[0]['c'])) for x in results)
    return dict(concept='restricted_constant_path_Nash_at_fixed_initial_state',certificate=certificate,
                runs=results,multiple_start_action_spread=spread,continuous_feedback_mpe_certified=False,
                unrestricted_open_loop_equilibrium_certified=False,parameters_empirically_identified=False)
