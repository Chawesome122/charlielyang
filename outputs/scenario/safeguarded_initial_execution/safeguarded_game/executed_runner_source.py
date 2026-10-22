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
from weaponized.game.hjb import StateGrid
from weaponized.game.primitives import GameParameters
from weaponized.game.safeguarded_iteration import solve_safeguarded_game

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--grids',nargs='+',type=int);parser.add_argument('--starts',nargs='+');parser.add_argument('--out',default='outputs/scenario/safeguarded_game')
    args=parser.parse_args();os.chdir(ROOT)
    config=yaml.safe_load((ROOT/'configs/safeguarded_game.yaml').read_text());base=yaml.safe_load((ROOT/config['base_config']).read_text())
    p=GameParameters(**base['parameters']).with_updates(**base['scenarios'][config['scenario']]);out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for size in args.grids or config['grids']:
        grid=StateGrid(size)
        for start in args.starts or config['starts']:
            print(f'RUN {config["scenario"]} {size}^4 {start}',flush=True)
            def report(row):
                if row['iteration']%10==0:print(f" iteration {row['iteration']}: gain={row['max_deviation_gain']:.4g} action={row['best_response_action_residual']:.4g}",flush=True)
            settings={k:config[k] for k in ['max_iterations','memory','ridge','damping','fallback_damping','backtracks','seed']}
            run=solve_safeguarded_game(grid,p,start,on_iteration=report,**settings)
            prefix=out/f'{config["scenario"]}_n{size}_{start}';archive=prefix.with_suffix('.npz')
            np.savez_compressed(archive,u=run['u'].reshape(grid.shape),c=run['c'].reshape(grid.shape),value_u=run['values'][0].reshape(grid.shape),value_c=run['values'][1].reshape(grid.shape),axis=grid.axes[0])
            diagnostic={k:v for k,v in run.items() if k not in {'u','c','values'}}
            diagnostic.update(scenario=config['scenario'],archive=str(archive.relative_to(ROOT)),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),registry_sha256=hashlib.sha256((ROOT/'configs/safeguarded_game.yaml').read_bytes()).hexdigest(),method_settings=settings)
            prefix.with_suffix('.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            rows.append({k:diagnostic[k] for k in ['scenario','grid_size','start','status','termination_reason','elapsed_seconds','max_deviation_gain','best_response_action_residual','policy_evaluations']})
            print(json.dumps(rows[-1]),flush=True)
    (out/'executed_attempts.json').write_text(json.dumps(dict(classification=config['classification'],continuous_mpe_certified=False,runs=rows),indent=2)+'\n')


if __name__=='__main__':main()
