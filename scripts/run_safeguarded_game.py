"""Execute separately registered safeguarded negative-adaptation experiments."""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'1')
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from scipy.interpolate import RegularGridInterpolator
from weaponized.game.hjb import StateGrid
from weaponized.game.primitives import GameParameters
from weaponized.game.safeguarded_iteration import solve_safeguarded_game
from weaponized.game.safeguarded_archive import verify_source_manifest,decode_saved_fields

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--grids',nargs='+',type=int);parser.add_argument('--starts',nargs='+');parser.add_argument('--out',default='outputs/scenario/safeguarded_game');parser.add_argument('--registry',default='configs/safeguarded_game.yaml')
    args=parser.parse_args();os.chdir(ROOT)
    verify_source_manifest(ROOT,json.loads((ROOT/'configs/safeguarded_reference_sources.json').read_text()))
    config=yaml.safe_load((ROOT/args.registry).read_text());base=yaml.safe_load((ROOT/config['base_config']).read_text())
    if config['thresholds']!={'deviation_gain':1e-8,'best_response_action':1e-7,'scaled_hjb':1e-8,'linear_rtol':1e-11}:raise ValueError('Original acceptance thresholds must remain unchanged')
    p=GameParameters(**base['parameters']).with_updates(**base['scenarios'][config['scenario']]);out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for size in args.grids or config['grids']:
        grid=StateGrid(size)
        for start in args.starts or config['starts']:
            print(f'RUN {config["scenario"]} {size}^4 {start}',flush=True)
            def report(row):
                if row['iteration']%10==0:print(f" iteration {row['iteration']}: gain={row['max_deviation_gain']:.4g} action={row['best_response_action_residual']:.4g}",flush=True)
            settings={k:config[k] for k in ['max_iterations','memory','ridge','damping','fallback_damping','backtracks','seed']}
            settings['merit_norm']=config.get('merit_norm','linf')
            initial=None;source=None;label=start
            if config.get('warm_start_grid'):
                source=ROOT/f"outputs/scenario/safeguarded_game/adaptation_negative_n{config['warm_start_grid']}_{start}.npz"
                source_record=json.loads(source.with_suffix('.json').read_text())
                if source_record['status']!='verified_finite_grid_candidate' or source_record['parameters']!=asdict(p) or hashlib.sha256(source.read_bytes()).hexdigest()!=source_record['archive_sha256']:raise ValueError('Invalid coarse warm-start candidate')
                blob=source.read_bytes()
                if hashlib.sha256(blob).hexdigest()!=config['warm_start_archives'][start]:raise ValueError('Registered warm-start hash mismatch')
                coarse_grid=StateGrid(config['warm_start_grid']);fields=decode_saved_fields(blob,source_record['archive_sha256'],coarse_grid)
                initial=np.r_[tuple(RegularGridInterpolator(coarse_grid.axes,field.reshape(coarse_grid.shape))(grid.states) for field in fields[:2])]
                label='coarse_'+start
            run=solve_safeguarded_game(grid,p,label,on_iteration=report,initial_actions=initial,**settings)
            prefix=out/f'{config["scenario"]}_n{size}_{label}';archive=prefix.with_suffix('.npz')
            np.savez_compressed(archive,u=run['u'].reshape(grid.shape),c=run['c'].reshape(grid.shape),value_u=run['values'][0].reshape(grid.shape),value_c=run['values'][1].reshape(grid.shape),axis=grid.axes[0])
            diagnostic={k:v for k,v in run.items() if k not in {'u','c','values'}}
            diagnostic.update(scenario=config['scenario'],archive=str(archive.relative_to(ROOT)),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),registry_sha256=hashlib.sha256((ROOT/args.registry).read_bytes()).hexdigest(),registry=args.registry,method_source_sha256=hashlib.sha256((ROOT/'src/weaponized/game/safeguarded_iteration.py').read_bytes()).hexdigest(),method_settings=settings,warm_start_archive=None if source is None else str(source.relative_to(ROOT)),warm_start_archive_sha256=None if source is None else hashlib.sha256(source.read_bytes()).hexdigest())
            prefix.with_suffix('.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            rows.append({k:diagnostic[k] for k in ['scenario','grid_size','start','status','termination_reason','elapsed_seconds','max_deviation_gain','best_response_action_residual','policy_evaluations']})
            print(json.dumps(rows[-1]),flush=True)
    (out/'executed_attempts.json').write_text(json.dumps(dict(classification=config['classification'],continuous_mpe_certified=False,runs=rows),indent=2)+'\n')


if __name__=='__main__':main()
