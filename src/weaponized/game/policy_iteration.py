"""Damped coupled policy iteration with explicit finite-grid diagnostics."""
from dataclasses import asdict
import resource
import time
import numpy as np
from .hjb import StateGrid, evaluate_policies, improve_policies, policy_deviation_gaps


def initial_policies(grid,name,seed=101):
    n=grid.count
    starts={"zero":(0.,0.),"one":(1.,1.),"us_only":(1.,0.),"china_only":(0.,1.),"mid":(.5,.5)}
    if name in starts:
        return tuple(np.full(n,v) for v in starts[name])
    if name=="random":
        rng=np.random.default_rng(seed)
        # Smooth random multilinear shapes, not independent node noise.
        features=np.column_stack((np.ones(n),grid.states))
        return tuple(np.clip(features@rng.normal(0,.35,5)+.5,0,1) for _ in range(2))
    raise ValueError(f"Unknown initial policy {name}")


def solve_feedback_game(state_grid,primitives,starts=("zero","one","us_only","china_only","mid","random"),
                        tolerances=None,on_run=None):
    """Return candidates for the finite-state approximation, never certify continuum MPE.

    Values are re-evaluated at final policies. Report a tiny linear evaluation
    residual separately from optimality: the former alone proves no Nash property.
    """
    grid=state_grid if isinstance(state_grid,StateGrid) else StateGrid(state_grid)
    settings={"max_iterations":80,"damping":.6,"gap_tolerance":1e-8,"action_tolerance":1e-7,
              "seed":101,"linear_rtol":1e-11}
    settings.update(tolerances or {})
    runs=[]
    for start in starts:
        began=time.perf_counter();u,c=initial_policies(grid,start,settings["seed"])
        values=None;history=[];failure=None;damping=settings["damping"];previous_change=np.inf
        for iteration in range(settings["max_iterations"]):
            try:
                values,evaluation=evaluate_policies(grid,primitives,u,c,values,settings["linear_rtol"])
                new_u,new_c,improvement=improve_policies(grid,primitives,values,u,c)
            except (RuntimeError,ArithmeticError) as error:
                failure=str(error);break
            gu,gc,bru,brc=policy_deviation_gaps(grid,primitives,values,u,c)
            gap=float(max(gu.max(),gc.max()))
            change=float(max(np.max(abs(new_u-u)),np.max(abs(new_c-c))))
            br_residual=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
            history.append({"iteration":iteration,"max_deviation_gain":gap,"action_change":change,
                            "best_response_action_residual":br_residual,"damping":damping,
                            "linear":evaluation,"improvement":improvement})
            if gap<=settings["gap_tolerance"] and br_residual<=settings["action_tolerance"] and not improvement["no_verified_pure_action_candidate_nodes"]:
                break
            if change>previous_change*1.05:
                damping=max(.1,damping*.75)
            previous_change=change
            u=(1-damping)*u+damping*new_u;c=(1-damping)*c+damping*new_c
        # Do not report stale values for updated policies.
        try:
            values,evaluation=evaluate_policies(grid,primitives,u,c,values,settings["linear_rtol"])
            gu,gc,bru,brc=policy_deviation_gaps(grid,primitives,values,u,c)
            gap=float(max(gu.max(),gc.max()));brres=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
            residuals=[x["linear_residual_inf"] for x in evaluation["players"]]
            passed=gap<=settings["gap_tolerance"] and brres<=settings["action_tolerance"] and all(
                item["linear_residual_inf"]<=1e-8*(1+item["reward_inf"]) for item in evaluation["players"])
        except RuntimeError as error:
            failure=str(error);evaluation={};gap=brres=np.inf;residuals=[];passed=False
        runs.append({"start":start,"status":"verified_finite_grid_candidate" if passed else "not_solved",
                     "continuous_mpe_certified":False,"parameters":asdict(primitives),"grid_size":grid.size,
                     "nodes":grid.count,"elapsed_seconds":time.perf_counter()-began,
                     "peak_process_rss_kib":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
                     "max_deviation_gain":gap,"best_response_action_residual":brres,"hjb_residuals":residuals,
                     "evaluation":evaluation,"failure":failure,"history":history,
                     "u":u,"c":c,"values":values})
        if on_run is not None:
            on_run(runs[-1])
    for i,result in enumerate(runs):
        result["pairwise_policy_sup_distances"]={other["start"]:float(max(np.max(abs(result["u"]-other["u"])),
                    np.max(abs(result["c"]-other["c"])))) for other in runs[:i]}
    return {"concept":"stationary_pure_candidate_of_finite_state_continuous_action_game",
            "continuous_mpe_certified":False,"settings":settings,"runs":runs}


def solve_alternating_game(state_grid,p,start="mid",max_outer=100,damping=.5,max_inner=30):
    """Alternate global discounted MDP best responses as a robustness attempt.

    Each player's inner policy iteration holds the opponent feedback policy
    fixed, and hence solves the correct unilateral dynamic-control problem.
    Outer best-response iteration need not converge in a general-sum game;
    final global gaps still determine acceptance. This is not an existence
    theorem or a repair that guarantees a solution.
    """
    grid=state_grid if isinstance(state_grid,StateGrid) else StateGrid(state_grid)
    u,c=initial_policies(grid,start);values=None;history=[];began=time.perf_counter()
    for outer in range(max_outer):
        values,evaluation=evaluate_policies(grid,p,u,c,values)
        gu,gc,bru,brc=policy_deviation_gaps(grid,p,values,u,c)
        gap=float(max(gu.max(),gc.max()));brres=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
        history.append({"iteration":outer,"max_deviation_gain":gap,"best_response_action_residual":brres,
                        "linear":evaluation,"method":"alternating_discounted_mdp_best_responses"})
        if gap<=1e-8 and brres<=1e-7:break
        proposed_u=u.copy();proposed_c=c.copy();trial_values=values
        inner_counts=[]
        for player in (0,1):
            for inner in range(max_inner):
                trial_values,_=evaluate_policies(grid,p,proposed_u,proposed_c,trial_values)
                igu,igc,ibu,ibc=policy_deviation_gaps(grid,p,trial_values,proposed_u,proposed_c)
                current=proposed_u if player==0 else proposed_c
                best=ibu if player==0 else ibc
                igap=igu if player==0 else igc
                if igap.max()<=1e-10 and np.max(abs(current-best))<=1e-8:break
                if player==0:proposed_u=best
                else:proposed_c=best
            inner_counts.append(inner+1)
        history[-1]["inner_iterations"]=inner_counts
        u=(1-damping)*u+damping*proposed_u;c=(1-damping)*c+damping*proposed_c
    values,evaluation=evaluate_policies(grid,p,u,c,values)
    gu,gc,bru,brc=policy_deviation_gaps(grid,p,values,u,c)
    gap=float(max(gu.max(),gc.max()));brres=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
    passed=gap<=1e-8 and brres<=1e-7 and all(z["linear_residual_inf"]<=1e-8*(1+z["reward_inf"]) for z in evaluation["players"])
    return {"start":start,"method":"alternating_discounted_mdp_best_responses",
            "status":"verified_finite_grid_candidate" if passed else "not_solved","continuous_mpe_certified":False,
            "parameters":asdict(p),"grid_size":grid.size,"nodes":grid.count,"elapsed_seconds":time.perf_counter()-began,
            "peak_process_rss_kib":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),"max_deviation_gain":gap,
            "best_response_action_residual":brres,"hjb_residuals":[z["linear_residual_inf"] for z in evaluation["players"]],
            "evaluation":evaluation,"history":history,"u":u,"c":c,"values":values,
            "pairwise_policy_sup_distances":{},"failure":None}
