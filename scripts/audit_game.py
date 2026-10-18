#!/usr/bin/env python3
"""Independently re-read and verify saved hypothetical finite-grid candidates."""
import os
for name in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ.setdefault(name,"1")
os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME","/tmp/weaponized-cache")
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weaponized.game.primitives import GameParameters,payoffs,dynamics
from weaponized.game.hjb import StateGrid,build_generator,policy_deviation_gaps,evaluate_policies
from weaponized.game.stability import feedback_stationary_point


def offgrid_diagnostics(grid,p,u,c,vu,vc,seed=123,n=256):
    rng=np.random.default_rng(seed);states=rng.uniform(.01,.99,(n,4))
    fields=[u,c,vu,vc]
    interp=[RegularGridInterpolator(grid.axes,field.reshape(grid.shape)) for field in fields]
    actions=[fn(states) for fn in interp[:2]];values=[fn(states) for fn in interp[2:]]
    gradients=[]
    for fn in interp[2:]:
        gradient=np.empty((n,4))
        for j in range(4):
            # Centered differences remain in the same multilinear grid cell.
            distance=np.min(abs(states[:,j,None]-grid.axes[j][None,:]),axis=1)
            step=np.minimum(1e-6,distance/4)
            lo=states.copy();hi=states.copy();lo[:,j]-=step;hi[:,j]+=step
            gradient[:,j]=(fn(hi)-fn(lo))/(2*step)
        gradients.append(gradient)
    drift=dynamics(states,*actions,p);rewards=payoffs(states,*actions,p)
    residuals=[rho*value-reward-np.sum(gradient*drift,axis=1)
               for rho,value,reward,gradient in zip((p.rho_u,p.rho_c),values,rewards,gradients)]
    mu=p.a_u*(1-states[:,0])+p.kappa_c*gradients[0][:,2]
    mc=p.a_c*(1-states[:,1])+p.kappa_u*gradients[1][:,3]
    bru=np.clip((mu+p.q_u*actions[1])/p.k_u,0,1)
    brc=np.clip((mc+p.q_c*actions[0])/p.k_c,0,1)
    gains=[(mu+p.q_u*actions[1])*(bru-actions[0])-.5*p.k_u*(bru**2-actions[0]**2),
           (mc+p.q_c*actions[0])*(brc-actions[1])-.5*p.k_c*(brc**2-actions[1]**2)]
    return {"classification":"diagnostic_of_interpolated_fields_not_equilibrium_certificate","seed":seed,"sample_size":n,
            "continuous_hjb_residual_inf":[float(np.max(abs(r))) for r in residuals],
            "continuous_hjb_residual_rmse":[float(np.sqrt(np.mean(r*r))) for r in residuals],
            "continuous_unilateral_gain_inf":[float(np.max(np.maximum(0,g))) for g in gains],
            "continuous_br_action_error_inf":[float(np.max(abs(bru-actions[0]))),float(np.max(abs(brc-actions[1])))],
            "warning":"Finite-grid acceptance thresholds do not apply to these nonzero continuum residuals."}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--out",type=Path,default=Path("outputs/scenario/game"))
    args=parser.parse_args();runs=[];representatives={};corrected_stability={}
    for path in sorted(args.out.rglob("*_n*_*.json")):
        diagnostic=json.loads(path.read_text())
        if "archive" not in diagnostic:continue
        arrays=Path(diagnostic["archive"]);actual_hash=hashlib.sha256(arrays.read_bytes()).hexdigest()
        data=np.load(arrays);size=diagnostic["grid_size"];grid=StateGrid(size)
        p=GameParameters(**diagnostic["parameters"])
        u,c,vu,vc=[data[name].ravel() for name in ("u","c","value_u","value_c")]
        gen=build_generator(grid,p,u,c);rewards=payoffs(grid.states,u,c,p)
        residuals=[float(np.max(abs(rho*value-reward-gen@value))) for rho,value,reward in zip((p.rho_u,p.rho_c),(vu,vc),rewards)]
        gu,gc,bru,brc=policy_deviation_gaps(grid,p,[vu,vc],u,c)
        gap=float(max(gu.max(),gc.max()));action=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
        valid=actual_hash==diagnostic["archive_sha256"] and gap<=1e-8 and action<=1e-7 and all(
            residual<=1e-8*(1+np.max(abs(reward))) for residual,reward in zip(residuals,rewards))
        if valid:
            stability=feedback_stationary_point(grid,u,c,p)
            diagnostic["closed_loop_stability"]=stability
            path.write_text(json.dumps(diagnostic,indent=2)+"\n")
            corrected_stability[str(arrays)]=stability
        runs.append({"diagnostic":str(path),"scenario":diagnostic["scenario"],"grid_size":size,"start":diagnostic["start"],
                     "reported_status":diagnostic["status"],
                     "checksum_pass":actual_hash==diagnostic["archive_sha256"],"passed_saved_candidate_verification":bool(valid),
                     "hjb_residuals":residuals,"max_unilateral_gain":gap,"best_response_action_residual":action})
        if valid:runs[-1]["closed_loop_stability"]=stability
        key=(diagnostic["scenario"],size)
        if valid and (key not in representatives or diagnostic["start"]=="zero"):
            representatives[key]=(grid,p,u,c,vu,vc)
    refinements=[];offgrid=[]
    for (scenario,size),(grid,p,u,c,vu,vc) in sorted(representatives.items()):
        item=offgrid_diagnostics(grid,p,u,c,vu,vc);item.update(scenario=scenario,grid_size=size);offgrid.append(item)
        smaller=sorted(n for sc,n in representatives if sc==scenario and n<size)
        if not smaller:continue
        coarse=smaller[-1];cg,_,cu,cc,cvu,cvc=representatives[(scenario,coarse)]
        up=[RegularGridInterpolator(cg.axes,field.reshape(cg.shape))(grid.states) for field in (cu,cc)]
        held_values,evaluation=evaluate_policies(grid,p,*up,[vu,vc])
        gu,gc,_,_=policy_deviation_gaps(grid,p,held_values,*up)
        refinements.append({"scenario":scenario,"coarse_grid":coarse,"fine_grid":size,
                            "u_sup_change":float(np.max(abs(u-up[0]))),"c_sup_change":float(np.max(abs(c-up[1]))),
                            "heldout_fine_grid_coarse_policy_deviation_gap":float(max(gu.max(),gc.max())),
                            "heldout_policy_evaluation":evaluation})
    result={"classification":"hypothetical_numerical_audit_not_empirical_results","continuous_mpe_certified":False,
            "archived_run_count":len(runs),
            "claimed_candidate_count":sum(r["reported_status"]=="verified_finite_grid_candidate" for r in runs),
            "not_solved_count":sum(r["reported_status"]=="not_solved" for r in runs),
            "all_claimed_candidates_pass":all(r["passed_saved_candidate_verification"] for r in runs if r["reported_status"]=="verified_finite_grid_candidate"),
            "all_archived_runs_satisfy_candidate_thresholds":all(r["passed_saved_candidate_verification"] for r in runs),
            "runs":runs,"grid_refinement":refinements,"offgrid_continuum_diagnostics":offgrid}
    # Refresh old execution summaries after the nonsmooth-knot stability repair.
    # Numerical policies/values and their archive checksums remain unchanged.
    for summary_path in args.out.glob("summary_*.json"):
        summary=json.loads(summary_path.read_text())
        for row in summary.get("runs",[]):
            if row.get("archive") in corrected_stability:
                row["closed_loop_stability"]=corrected_stability[row["archive"]]
        summary_path.write_text(json.dumps(summary,indent=2)+"\n")
    (args.out/"independent_saved_candidate_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    if refinements:
        fig,ax=plt.subplots(figsize=(6,3.5),layout="constrained")
        for scenario in sorted(set(r["scenario"] for r in refinements)):
            selected=[r for r in refinements if r["scenario"]==scenario]
            ax.plot([r["fine_grid"] for r in selected],[max(r["u_sup_change"],r["c_sup_change"]) for r in selected],"o-",label=scenario)
        ax.set(xlabel="Nodes per state dimension (finer mesh)",ylabel="Policy sup change from preceding mesh",yscale="log",title="Hypothetical game: grid sensitivity, no continuum certificate")
        ax.legend(fontsize=8);fig.savefig(args.out/"mesh_refinement.pdf");fig.savefig(args.out/"mesh_refinement.png",dpi=180);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ("runs","offgrid_continuum_diagnostics")},indent=2))


if __name__=="__main__":main()
