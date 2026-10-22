"""Recompute saved-array status and exhibits for all registered solver variants."""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'1')
os.environ.setdefault('MPLCONFIGDIR','/tmp/weaponized-matplotlib')
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from weaponized.game.hjb import StateGrid
from weaponized.game.primitives import GameParameters
from weaponized.game.safeguarded_archive import audit_saved_response,decode_saved_fields,verify_source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT);source_manifest=json.loads(Path('configs/safeguarded_reference_sources.json').read_text());reference_checks=verify_source_manifest(ROOT,source_manifest);rows=[];histories=[];nodes=[];source_checks=[]
    base=yaml.safe_load(Path('configs/game.yaml').read_text());p=GameParameters(**base['parameters']).with_updates(**base['scenarios']['adaptation_negative'])
    families=[('linf','configs/safeguarded_game.yaml','outputs/scenario/safeguarded_game'),('rms','configs/safeguarded_game_rms.yaml','outputs/scenario/safeguarded_game_rms'),('coarse_interpolation','configs/safeguarded_game_coarse.yaml','outputs/scenario/safeguarded_game_coarse')]
    for family,registration,folder in families:
        config=yaml.safe_load(Path(registration).read_text());out=Path(folder)
        for size in config['grids']:
            grid=StateGrid(size)
            for start in config['starts']:
                label=('coarse_' if config.get('warm_start_grid') else '')+start
                path=out/f'adaptation_negative_n{size}_{label}.json';record=json.loads(path.read_text())
                if record['parameters']!=asdict(p) or record['grid_size']!=size or record['start']!=label or record['scenario']!='adaptation_negative':raise ValueError('Unregistered saved model, grid or initialization')
                if record['registry_sha256']!=hashlib.sha256(Path(registration).read_bytes()).hexdigest():raise ValueError('Registration hash mismatch')
                if len(record['history'])>config['max_iterations']:raise ValueError('Saved iteration budget exceeded')
                blob=Path(record['archive']).read_bytes()
                if hashlib.sha256(blob).hexdigest()!=record['archive_sha256']:raise ValueError('Archive hash mismatch')
                fields=decode_saved_fields(blob,record['archive_sha256'],grid)
                independent=audit_saved_response(grid,p,*fields,record['status'])
                if record.get('method_source_sha256')!=hashlib.sha256(Path('src/weaponized/game/safeguarded_iteration.py').read_bytes()).hexdigest():raise ValueError('Current attempt does not use the final registered numerical method source')
                if config.get('warm_start_grid'):
                    source=Path(record['warm_start_archive']);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
                    if source_hash!=record['warm_start_archive_sha256'] or source_hash!=config['warm_start_archives'][start]:raise ValueError('Coarse warm-start provenance mismatch')
                source_checks.append(dict(family=family,grid=size,start=label,registration_sha256=record['registry_sha256'],archive_sha256=record['archive_sha256'],checked=True))
                row=dict(family=family,grid_size=size,nodes=grid.count,start=label,iterations=len(record['history']),termination=record['termination_reason'],policy_evaluations=record['policy_evaluations'],elapsed_seconds=record['elapsed_seconds'],**independent)
                rows.append(row)
                histories.extend(dict(family=family,grid_size=size,start=label,iteration=h['iteration'],global_gain=h['max_deviation_gain'],action_residual=h['best_response_action_residual'],search_merit=h['merit'],evaluations=h['evaluations']) for h in record['history'])
    out=Path('outputs/scenario/safeguarded_analysis');out.mkdir(parents=True,exist_ok=True)
    attempts=pd.DataFrame(rows);attempts['max_hjb_residual']=attempts.hjb_residuals.map(max);attempts.drop(columns='hjb_residuals').to_csv(out/'attempts.csv',index=False)
    summary=attempts.groupby(['family','grid_size'],sort=False).agg(attempts=('start','size'),accepted=('accepted_finite_grid_candidate','sum'),min_gain=('max_unilateral_gain','min'),max_gain=('max_unilateral_gain','max'),min_action=('best_response_action_residual','min'),max_action=('best_response_action_residual','max')).reset_index()
    summary.to_csv(out/'summary_table.csv',index=False)
    lines=[r'\begin{tabular}{llrrrr}\toprule',r'Search & Grid & Accepted & Attempts & Max gain & Max action error \\\midrule']
    for row in summary.to_dict('records'):
        lines.append(f"{row['family'].replace('_',' ')} & {row['grid_size']}$^4$ & {row['accepted']} & {row['attempts']} & {row['max_gain']:.2g} & {row['max_action']:.2g}"+r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    (out/'scenario_table.tex').write_text('\n'.join(lines)+'\n')
    pd.DataFrame(histories).to_csv(out/'iteration_history.csv',index=False);pd.DataFrame(source_checks).to_csv(out/'archive_integrity.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    colors={'linf':'#246b91','rms':'#c35b24','coarse_interpolation':'#418a48'}
    labels={'linf':'L-infinity merit','rms':'RMS merit','coarse_interpolation':'Coarse-grid initialization'}
    for family in colors:
        part=pd.DataFrame(histories);part=part[(part.family==family)&(part.grid_size==17)]
        for start,group in part.groupby('start',sort=False):
            axes[0].semilogy(group.iteration,np.maximum(group.global_gain,1e-16),color=colors[family],alpha=.6,label=labels[family] if start==part.start.iloc[0] else None)
            axes[1].semilogy(group.iteration,np.maximum(group.action_residual,1e-16),color=colors[family],alpha=.6,label=labels[family] if start==part.start.iloc[0] else None)
    for ax,threshold,title in zip(axes,[1e-8,1e-7],['Global unilateral gain','Global action residual']):
        ax.axhline(threshold,color='black',ls='--',lw=.8,label='Original acceptance threshold');ax.set(xlabel='Accepted search iteration',ylabel='Residual',title=title);ax.grid(alpha=.2);ax.legend(fontsize=7)
    fine_failures=int(((attempts.grid_size==17)&~attempts.accepted_finite_grid_candidate).sum())
    fig.suptitle(f'Hypothetical negative-adaptation search: {fine_failures} additional 17⁴ failures',fontsize=11);fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(out/f'convergence.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    result=dict(passed=all(r['status_consistent'] for r in rows),classification='hypothetical_numerical_method_robustness_not_empirical',registered_attempts=len(rows),accepted_coarse_candidates=int(((attempts.grid_size==7)&attempts.accepted_finite_grid_candidate).sum()),accepted_fine_candidates=int(((attempts.grid_size==17)&attempts.accepted_finite_grid_candidate).sum()),not_solved=int((~attempts.accepted_finite_grid_candidate).sum()),archive_integrity_checks=len(source_checks),reference_source_checks=reference_checks,continuous_mpe_certified=False,nonexistence_proved=False,thresholds_relaxed=False,original_core_modified=False)
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
