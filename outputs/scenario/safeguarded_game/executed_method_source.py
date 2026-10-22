"""Safeguarded Anderson search for the original finite-grid Bellman fixed point.

Only the iteration changes. Every policy evaluation, global unilateral maximizer,
state-constrained stencil and acceptance threshold uses the original HJB module.
Neither successful finite-grid search nor iteration failure certifies continuum
MPE existence/nonexistence. Anderson proposals have no convergence guarantee here.
"""
from dataclasses import asdict
import resource
import time

import numpy as np

from .hjb import StateGrid, evaluate_policies, policy_deviation_gaps
from .policy_iteration import initial_policies


def anderson_proposal(points, residuals, damping=1., memory=6, ridge=1e-10):
    """Type-II multisecant step with relative Tikhonov regularization.

    Least squares fits differences of the evaluated global best-response map's
    residual. Box projection is a numerical admissibility operation, never a
    replacement for simultaneous best-response or final Nash verification.
    """
    if not points or len(points) != len(residuals) or memory < 0 or ridge < 0 or not 0 < damping <= 1:
        raise ValueError('Consistent nonempty histories and valid Anderson settings required')
    x=np.asarray(points[-1],dtype=float);r=np.asarray(residuals[-1],dtype=float)
    if x.ndim!=1 or x.shape!=r.shape or not np.isfinite(x).all() or not np.isfinite(r).all():
        raise ValueError('Finite one-dimensional action/residual vectors required')
    count=min(memory,len(points)-1)
    if not count:return np.clip(x+damping*r,0,1),dict(memory_used=0,coefficient_l1=0.)
    xp=np.asarray(points[-count-1:]);rp=np.asarray(residuals[-count-1:])
    dx=np.diff(xp,axis=0).T;dr=np.diff(rp,axis=0).T
    gram=dr.T@dr;scale=max(float(np.trace(gram))/count,np.finfo(float).tiny)
    gamma=np.linalg.lstsq(gram+ridge*scale*np.eye(count),dr.T@r,rcond=1e-12)[0]
    proposal=x+damping*r-(dx+damping*dr)@gamma
    if not np.isfinite(proposal).all():raise ArithmeticError('Nonfinite Anderson proposal')
    return np.clip(proposal,0,1),dict(memory_used=count,coefficient_l1=float(np.sum(abs(gamma))))


def evaluated_response(grid,p,actions,initial_values=None,linear_rtol=1e-11,merit_norm="linf"):
    """Evaluate current policy and its exact global unilateral Hamiltonian BRs."""
    actions=np.asarray(actions,dtype=float)
    if actions.shape!=(2*grid.count,) or not np.isfinite(actions).all() or np.any((actions<0)|(actions>1)):
        raise ValueError('Bounded policy arrays on the selected four-state grid required')
    u,c=actions[:grid.count],actions[grid.count:]
    values,evaluation=evaluate_policies(grid,p,u,c,initial_values,linear_rtol)
    gu,gc,bru,brc=policy_deviation_gaps(grid,p,values,u,c)
    residual=np.r_[bru-u,brc-c]
    gap=float(max(gu.max(),gc.max()));action=float(np.max(abs(residual)))
    # This merit is only a search aid. Acceptance tests each original criterion.
    if merit_norm not in {'linf','rms'}:raise ValueError('Unknown residual merit norm')
    merit=max(action,float(np.sqrt(2*gap/min(p.k_u,p.k_c)))) if merit_norm=='linf' else float(np.sqrt(np.mean(residual**2)))
    return dict(values=values,evaluation=evaluation,residual=residual,gap=gap,action=action,merit=merit)


def accepted_response(response,gain_tolerance=1e-8,action_tolerance=1e-7):
    return bool(response['gap']<=gain_tolerance and response['action']<=action_tolerance and all(
        e['linear_residual_inf']<=1e-8*(1+e['reward_inf']) for e in response['evaluation']['players']))


def solve_safeguarded_game(state_grid,p,start='zero',max_iterations=120,memory=6,ridge=1e-10,
                           damping=.8,fallback_damping=.05,backtracks=5,seed=101,merit_norm="linf",initial_actions=None,on_iteration=None):
    """Residual-decreasing accelerated search, with an explicit not-solved exit.

    Each trial is freshly policy-evaluated. Try the projected Anderson direction
    and backtrack; if it fails to decrease merit, try the relaxed global-BR
    direction. If no evaluated trial improves merit, stop and preserve the best
    actual arrays. Do not report a projected proposal or stale values as solved.
    """
    if max_iterations<=0 or memory<0 or ridge<0 or not 0<damping<=1 or not 0<fallback_damping<=1 or backtracks<0:
        raise ValueError('Invalid safeguarded-iteration settings')
    grid=state_grid if isinstance(state_grid,StateGrid) else StateGrid(state_grid)
    began=time.perf_counter();x=np.r_[initial_policies(grid,start,seed)] if initial_actions is None else np.asarray(initial_actions,dtype=float).copy()
    current=evaluated_response(grid,p,x,merit_norm=merit_norm);points=[x.copy()];residuals=[current['residual'].copy()]
    history=[];evaluations=1;reason='iteration_budget_exhausted'
    for iteration in range(max_iterations):
        row=dict(iteration=iteration,max_deviation_gain=current['gap'],best_response_action_residual=current['action'],
                 merit=current['merit'],linear=current['evaluation'],evaluations=evaluations)
        history.append(row)
        if on_iteration:on_iteration(row)
        if accepted_response(current):reason='original_acceptance_thresholds_satisfied';break
        proposal,acceleration=anderson_proposal(points,residuals,damping,memory,ridge)
        row['anderson']=acceleration;best=None;best_x=None
        # A single accepted improving trial avoids unnecessary costly evaluations.
        for method,direction in [('anderson',proposal-x),('relaxed_global_br',fallback_damping*current['residual'])]:
            for bt in range(backtracks+1):
                step=2.**(-bt);trial_x=np.clip(x+step*direction,0,1)
                if np.max(abs(trial_x-x))<1e-15:continue
                trial=evaluated_response(grid,p,trial_x,current['values'],merit_norm=merit_norm);evaluations+=1
                if best is None or trial['merit']<best['merit']:best,best_x=trial,trial_x
                if accepted_response(trial) or trial['merit']<current['merit']*(1-1e-4*step):
                    row.update(accepted_method=method,accepted_step=step,trial_evaluations=evaluations-row['evaluations'])
                    break
            else:continue
            break
        if best is None or not (accepted_response(best) or best['merit']<current['merit']):
            reason='no_residual_decreasing_evaluated_direction';break
        x=best_x;current=best;points.append(x.copy());residuals.append(current['residual'].copy())
        if len(points)>memory+1:points.pop(0);residuals.pop(0)
    # Re-evaluate saved arrays independently of the trial's warm-started values.
    final=evaluated_response(grid,p,x,merit_norm=merit_norm);evaluations+=1
    passed=accepted_response(final)
    if passed:reason='original_acceptance_thresholds_satisfied'
    return dict(start=start,status='verified_finite_grid_candidate' if passed else 'not_solved',
                method='safeguarded_anderson_global_hamiltonian_best_response',continuous_mpe_certified=False,
                parameters=asdict(p),grid_size=grid.size,nodes=grid.count,
                elapsed_seconds=time.perf_counter()-began,peak_process_rss_kib=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
                max_deviation_gain=final['gap'],best_response_action_residual=final['action'],
                hjb_residuals=[e['linear_residual_inf'] for e in final['evaluation']['players']],
                evaluation=final['evaluation'],failure=None,termination_reason=reason,history=history,
                policy_evaluations=evaluations,u=x[:grid.count],c=x[grid.count:],values=final['values'])
