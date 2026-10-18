#!/usr/bin/env python3
"""Execute hypothetical game benchmarks and fully diagnosed finite-grid candidates.

Examples:
  uv run python scripts/run_game.py --grids 5 --scenarios adaptation_positive
  uv run python scripts/run_game.py --grids 17 21 --scenarios adaptation_positive
  uv run python scripts/run_game.py --grids 7 --scenarios adaptation_negative adaptation_zero
"""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time
# These sparse solves are memory bound. Unbounded BLAS thread pools make short
# vector reductions disproportionately expensive on shared cloud CPUs.
for _thread_env in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_env,"1")
import numpy as np
import yaml
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator
os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME","/tmp/weaponized-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weaponized.game.primitives import GameParameters,dynamics,payoffs
from weaponized.game.benchmark import solve_constant_control,constant_control_objective
from weaponized.game.hjb import StateGrid
from weaponized.game.policy_iteration import solve_feedback_game,solve_alternating_game
from weaponized.game.stability import feedback_stationary_point,interpolated_policy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_safe(value):
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_safe(v) for v in value]
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,(np.floating,float)) and not np.isfinite(value):return None
    return value


def run_trajectories(grid,run,p,path_prefix):
    """Deterministic theoretical counterfactuals; none is observed policy."""
    policy=interpolated_policy(grid,run["u"],run["c"])
    state0=np.array([.25,.25,0.,0.]);c0=policy(state0)[1]
    paths={}
    for experiment in ("candidate_feedback","controls_25pct_higher","controls_25pct_lower","us_shock_one_year"):
        def controls(t,s):
            u,c=policy(np.clip(s,0,1))
            if experiment=="controls_25pct_higher":return min(1,1.25*u),min(1,1.25*c)
            if experiment=="controls_25pct_lower":return .75*u,.75*c
            if experiment=="us_shock_one_year" and t<1:return min(1,u+.25),c0
            return u,c
        def field(t,z):
            u,c=controls(t,z[:4]);pr=payoffs(z[:4],u,c,p)
            return np.concatenate((dynamics(z[:4],u,c,p),[np.exp(-p.rho_u*t)*pr[0],np.exp(-p.rho_c*t)*pr[1]]))
        # Split at a control discontinuity to avoid silently stepping across it.
        times=np.arange(0,30.0001,.25)
        if experiment=="us_shock_one_year":
            a=solve_ivp(field,(0,1),np.r_[state0,0.,0.],t_eval=times[times<1],rtol=1e-8,atol=1e-10,max_step=.05,dense_output=True)
            b=solve_ivp(field,(1,30),a.sol(1),t_eval=times[times>=1],rtol=1e-8,atol=1e-10,max_step=.2)
            trajectory=np.concatenate((a.y,b.y),axis=1).T
            success=a.success and b.success
        else:
            result=solve_ivp(field,(0,30),np.r_[state0,0.,0.],t_eval=times,rtol=1e-8,atol=1e-10,max_step=.2)
            trajectory=result.y.T;success=result.success
        if not success or trajectory[:,:4].min()<-1e-8 or trajectory[:,:4].max()>1+1e-8:
            raise RuntimeError("Counterfactual integration failed or left invariant state cube")
        actions=np.array([controls(t,s) for t,s in zip(times,trajectory[:,:4])])
        table=np.column_stack((times,trajectory[:,:4],actions,trajectory[:,4:]))
        csv_path=path_prefix.with_name(path_prefix.name+f"_{experiment}.csv")
        np.savetxt(csv_path,table,delimiter=",",header="year,x,y,m,n,u,c,discounted_payoff_us_through_year,discounted_payoff_china_through_year",comments="")
        paths[experiment]={"year":times,"states":trajectory[:,:4],"actions":actions,
                           "discounted_30_year_payoffs":trajectory[-1,4:].tolist(),"csv":str(csv_path),
                           "payoff_scope":"finite_30_year_integral_no_terminal_continuation"}
    return paths


def figures(out,scenario,grid,run,p,paths):
    prefix=out/f"{scenario}_n{grid.size}"
    fig,axes=plt.subplots(1,2,figsize=(8,3.3),layout="constrained")
    mid=grid.size//2
    for ax,field,title in zip(axes,(run["u"],run["c"]),("U.S. restriction u","Chinese restriction c")):
        values=field.reshape(grid.shape)[:,:,mid,mid]
        image=ax.imshow(values.T,origin="lower",extent=[0,1,0,1],vmin=0,vmax=1,aspect="equal",cmap="viridis")
        ax.set(xlabel="Domestic capability x",ylabel="China-free resilience y",title=title)
    fig.colorbar(image,ax=axes,label="Scenario action")
    fig.suptitle(f"Hypothetical finite-grid candidate ({scenario}, {grid.size}⁴); m=n=0.5",fontsize=10)
    fig.savefig(str(prefix)+"_policy.pdf");fig.savefig(str(prefix)+"_policy.png",dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(8,5.5),layout="constrained")
    for label,item in paths.items():
        t=item["year"];s=item["states"];a=item["actions"]
        for axis,series in zip(axes.flat,(s[:,0],s[:,1],a[:,0],a[:,1])):
            axis.plot(t,series,label=label.replace("_"," "))
    for ax,name in zip(axes.flat,("Domestic capability x","China-free resilience y","U.S. restriction u","Chinese restriction c")):
        ax.set(xlabel="Years",ylabel=name,ylim=(0,1));ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=6)
    fig.suptitle(f"Hypothetical scenarios, no empirical calibration ({scenario})",fontsize=10)
    fig.savefig(str(prefix)+"_trajectories.pdf");fig.savefig(str(prefix)+"_trajectories.png",dpi=180);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grids",type=int,nargs="+",default=[5])
    parser.add_argument("--scenarios",nargs="+",default=["adaptation_positive"])
    parser.add_argument("--starts",nargs="+",default=["zero","one","us_only","china_only","mid","random"])
    parser.add_argument("--max-iterations",type=int,default=80)
    parser.add_argument("--method",choices=["joint","alternating"],default="joint")
    parser.add_argument("--out",type=Path,default=Path("outputs/scenario/game"))
    parser.add_argument("--no-figures",action="store_true")
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    config=yaml.safe_load(Path("configs/game.yaml").read_text());base=GameParameters(**config["parameters"])
    benchmark=solve_constant_control()
    (args.out/"constant_control_benchmark.json").write_text(json.dumps(benchmark,indent=2)+"\n")
    controls=np.linspace(0,1,301)
    np.savetxt(args.out/"constant_control_benchmark.csv",np.c_[controls,constant_control_objective(controls)],
               delimiter=",",header="constant_control,discounted_objective_synthetic",comments="")
    if not args.no_figures:
        fig,ax=plt.subplots(figsize=(5.5,3.3),layout="constrained")
        ax.plot(controls,constant_control_objective(controls));ax.axvline(benchmark["policy"],color="C1",ls="--",label=f"Constant-policy optimum {benchmark['policy']:.6f}")
        ax.axvline(1,color="C2",ls=":",label="Myopic action 1")
        ax.set(xlabel="Constant restriction intensity",ylabel="Discounted scenario payoff",title="One-sided self-eroding leverage: hypothetical benchmark");ax.legend(fontsize=8)
        fig.savefig(args.out/"constant_control_benchmark.pdf");fig.savefig(args.out/"constant_control_benchmark.png",dpi=180);plt.close(fig)
    summary={"classification":"hypothetical_scenarios_not_empirical_results","information_freeze":"2026-10-11",
             "algorithm":{"method":args.method,"max_iterations":args.max_iterations,"starts":args.starts},
             "config_sha256":digest(Path("configs/game.yaml")),"benchmark":benchmark,"runs":[],"grid_refinement":[]}
    previous={}
    for scenario in args.scenarios:
        if scenario not in config["scenarios"]:parser.error(f"Unknown scenario: {scenario}")
        p=base.with_updates(**config["scenarios"][scenario])
        for size in args.grids:
            grid=StateGrid(size)
            print(f"RUN scenario={scenario} grid={size} nodes={grid.count} starts={args.starts}",flush=True)
            def checkpoint(run):
                # Persist each start immediately. An interruption must not erase
                # already executed starts while later starts are still running.
                name=f"{scenario}_n{size}_{run['start']}"
                archive=args.out/(name+".npz")
                arrays={"u":run["u"].reshape(grid.shape),"c":run["c"].reshape(grid.shape),"axis":grid.axes[0]}
                if run["values"] is not None:
                    arrays.update(value_u=run["values"][0].reshape(grid.shape),value_c=run["values"][1].reshape(grid.shape))
                np.savez_compressed(archive,**arrays)
                diagnostic={k:v for k,v in run.items() if k not in ("u","c","values")}
                diagnostic.update(scenario=scenario,archive=str(archive),archive_sha256=digest(archive),checkpoint_phase="start_completed")
                (args.out/(name+".json")).write_text(json.dumps(json_safe(diagnostic),indent=2)+"\n")
                print(f"CHECKPOINT {name}: {run['status']}; seconds={run['elapsed_seconds']:.2f}",flush=True)
            if args.method=="joint":
                result=solve_feedback_game(grid,p,args.starts,{"max_iterations":args.max_iterations},on_run=checkpoint)
            else:
                result={"runs":[solve_alternating_game(grid,p,start,max_outer=args.max_iterations) for start in args.starts]}
            for run in result["runs"]:
                name=f"{scenario}_n{size}_{run['start']}"
                arrays_path=args.out/(name+".npz")
                np.savez_compressed(arrays_path,u=run["u"].reshape(grid.shape),c=run["c"].reshape(grid.shape),
                                    value_u=run["values"][0].reshape(grid.shape),value_c=run["values"][1].reshape(grid.shape),axis=grid.axes[0])
                diagnostics={k:v for k,v in run.items() if k not in ("u","c","values")}
                diagnostics["scenario"]=scenario;diagnostics["archive"]=str(arrays_path);diagnostics["archive_sha256"]=digest(arrays_path)
                if run["status"]=="verified_finite_grid_candidate":
                    diagnostics["closed_loop_stability"]=feedback_stationary_point(grid,run["u"],run["c"],p)
                (args.out/(name+".json")).write_text(json.dumps(json_safe(diagnostics),indent=2)+"\n")
                summary["runs"].append({k:v for k,v in diagnostics.items() if k!="history"})
                print(f"RESULT {name}: {run['status']}; gap={run['max_deviation_gain']:.3g}; action_residual={run['best_response_action_residual']:.3g}; seconds={run['elapsed_seconds']:.2f}",flush=True)
            representative=next((r for r in result["runs"] if r["status"]=="verified_finite_grid_candidate"),None)
            if representative:
                if scenario in previous:
                    oldgrid,old=previous[scenario]
                    coarse_u=RegularGridInterpolator(oldgrid.axes,old["u"].reshape(oldgrid.shape))(grid.states)
                    coarse_c=RegularGridInterpolator(oldgrid.axes,old["c"].reshape(oldgrid.shape))(grid.states)
                    summary["grid_refinement"].append({"scenario":scenario,"coarse":oldgrid.size,"fine":size,
                      "u_sup_change":float(np.max(abs(representative["u"]-coarse_u))),
                      "c_sup_change":float(np.max(abs(representative["c"]-coarse_c))),
                      "comparison":"coarse_multilinear_policy_evaluated_at_fine_grid_nodes"})
                previous[scenario]=(grid,representative)
                paths=run_trajectories(grid,representative,p,args.out/f"{scenario}_n{size}")
                summary["runs"][-len(result["runs"])]["counterfactuals"]={k:{kk:vv for kk,vv in v.items() if kk not in ("year","states","actions")} for k,v in paths.items()}
                if not args.no_figures:figures(args.out,scenario,grid,representative,p,paths)
            summary_file=args.out/("summary_"+"_".join(args.scenarios)+"_"+"_".join(map(str,args.grids))+".json")
            summary_file.write_text(json.dumps(json_safe(summary),indent=2)+"\n")
    print(f"Wrote {summary_file}",flush=True)


if __name__=="__main__":main()
