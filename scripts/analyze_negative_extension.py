"""Validate extra negative-beta runs and report numerical failures honestly."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path

for key in ["OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"]:
    os.environ.setdefault(key,"1")
os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from weaponized.game.hjb import StateGrid, policy_deviation_gaps
from weaponized.game.primitives import GameParameters

ROOT=Path(__file__).resolve().parents[1]


def main():
    registry=yaml.safe_load((ROOT/"configs/negative_beta_extension.yaml").read_text())
    base=yaml.safe_load((ROOT/registry["base_config"]).read_text())
    p=GameParameters(**base["parameters"]).with_updates(**base["scenarios"][registry["scenario"]])
    if hashlib.sha256((ROOT/"src/weaponized/game/policy_iteration.py").read_bytes()).hexdigest()!=registry["solver_source_sha256"]:
        raise ValueError("Extra-run registry's solver source changed")
    out=ROOT/registry["output"]
    audit=json.loads((out/"independent_saved_candidate_audit.json").read_text())
    if audit["archived_run_count"]!=len(registry["starts"]):
        raise ValueError("Incomplete or unregistered extra-run archive")
    checks=[];rows=[];nodes=[];history_rows=[]
    grid=StateGrid(registry["grid"])
    for start in registry["starts"]:
        diagnostic=out/f"{registry['scenario']}_n{grid.size}_{start}.json"
        run=json.loads(diagnostic.read_text())
        verified=next(r for r in audit["runs"] if r["start"]==start)
        if run["parameters"]!=asdict(p) or run["grid_size"]!=grid.size or run["start"]!=start or len(run["history"])>registry["max_iterations"]:
            raise ValueError("Extra run differs from registered parameters/grid/start/budget")
        archive=ROOT/run["archive"]
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        with np.load(archive) as data:
            u,c,vu,vc=[data[k].ravel() for k in ["u","c","value_u","value_c"]]
            if any(len(a)!=grid.count or not np.isfinite(a).all() for a in [u,c,vu,vc]) or not np.array_equal(data['axis'],grid.axes[0]):
                raise ValueError("Invalid finite-grid policy/value archive")
        bounded=bool(min(u.min(),c.min())>=0 and max(u.max(),c.max())<=1)
        consistent=(run["status"]=="verified_finite_grid_candidate")==verified["passed_saved_candidate_verification"]
        checks.append(bool(bounded and consistent and verified["checksum_pass"] and digest==run["archive_sha256"]))
        gu,gc,bru,brc=policy_deviation_gaps(grid,p,[vu,vc],u,c)
        gain=np.maximum(gu,gc);error=np.maximum(abs(bru-u),abs(brc-c))
        threshold=registry["unchanged_thresholds"]
        violating=(gain>threshold["deviation_gain"]) | (error>threshold["best_response_action"])
        row=dict(start=start,grid_size=grid.size,nodes=grid.count,iterations=len(run["history"]),
                 reported_status=run["status"],accepted_finite_grid_candidate=verified["passed_saved_candidate_verification"],
                 max_unilateral_gain=verified["max_unilateral_gain"],best_response_action_residual=verified["best_response_action_residual"],
                 max_hjb_policy_evaluation_residual=max(verified["hjb_residuals"]),
                 violating_grid_nodes=int(violating.sum()),unweighted_violating_grid_fraction=float(violating.mean()),
                 continuous_mpe_certified=False,empirical_parameter_estimate=False)
        rows.append(row)
        for rank,index in enumerate(np.argsort(-error,kind="stable")[:10],1):
            state=grid.states[index]
            nodes.append(dict(start=start,rank_by_action_error=rank,grid_index=int(index),
                              **dict(zip(["x","y","m","n"],state)),u=u[index],c=c[index],best_u=bru[index],best_c=brc[index],
                              us_unilateral_gain=gu[index],china_unilateral_gain=gc[index],
                              max_action_error=error[index],u_minus_m=u[index]-state[2],c_minus_n=c[index]-state[3]))
        for h in run["history"]:
            history_rows.append(dict(start=start,iteration=h["iteration"],max_unilateral_gain=h["max_deviation_gain"],
                                     best_response_action_residual=h["best_response_action_residual"],damping=h["damping"]))
    if not all(checks):
        raise ValueError("Archive checksum/domain/status does not match independent global deviation checks")
    pd.DataFrame(rows).to_csv(out/"registered_attempts.csv",index=False)
    pd.DataFrame(nodes).to_csv(out/"largest_action_residual_nodes.csv",index=False)
    pd.DataFrame(history_rows).to_csv(out/"iteration_history.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(9.5,3.9))
    history=pd.DataFrame(history_rows)
    for start,part in history.groupby('start',sort=False):
        axes[0].semilogy(part.iteration,np.maximum(part.max_unilateral_gain,1e-16),label=start)
        axes[1].semilogy(part.iteration,np.maximum(part.best_response_action_residual,1e-16),label=start)
    for ax,key,title in zip(axes,["deviation_gain","best_response_action"],["Global unilateral-deviation gain","Best-response action residual"]):
        ax.axhline(registry['unchanged_thresholds'][key],color='black',ls='--',lw=.8,label='Acceptance threshold')
        ax.set(xlabel='Policy-iteration step',ylabel='Residual',title=title);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Negative-adaptation scenario: additional 17⁴ initializations',fontsize=11)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(out/f"solver_diagnostics.{ext}",dpi=220,bbox_inches='tight')
    plt.close(fig)
    lines=[r"\begin{tabular}{lrrrr}\toprule",r"Start & Iterations & Deviation gain & Action residual & Linear residual \\\midrule"]
    for row in rows:
        lines.append(f"{row['start']} & {row['iterations']} & {row['max_unilateral_gain']:.2g} & {row['best_response_action_residual']:.2g} & {row['max_hjb_policy_evaluation_residual']:.2g}"+r" \\")
    lines.append(r"\bottomrule\end{tabular}")
    (ROOT/'manuscript/negative_extension_table.tex').write_text('\n'.join(lines)+'\n')
    result=dict(passed=all(checks),classification='hypothetical_numerical_robustness_not_empirical',
                registered_attempts=len(rows),accepted_finite_grid_candidates=sum(r['accepted_finite_grid_candidate'] for r in rows),
                not_solved=sum(not r['accepted_finite_grid_candidate'] for r in rows),
                every_registered_archive_integrity_and_status_checked=True,
                unchanged_deviation_gain_threshold=registry['unchanged_thresholds']['deviation_gain'],
                unchanged_action_threshold=registry['unchanged_thresholds']['best_response_action'],
                parameters_empirically_identified=False,continuous_mpe_certified=False,
                nonexistence_proved=False,independent_machine=False,
                unweighted_grid_node_fraction_is_an_empirical_probability=False,
                scope='Additional existing-solver initializations with unchanged economic parameters and acceptance thresholds; finite-grid numerical diagnostics only')
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
