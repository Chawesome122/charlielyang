"""Independent original-HJB checks of saved safeguarded experiment records.

Uses original model/HJB functions, not the new solver's acceptance/audit helpers.
This is internal computational review, not external or interval certification.
"""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'1')
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import hashlib,io,json
import numpy as np
import yaml
from scipy.interpolate import RegularGridInterpolator
from weaponized.game.hjb import StateGrid,build_generator,policy_deviation_gaps,evaluate_policies
from weaponized.game.policy_iteration import initial_policies
from weaponized.game.primitives import GameParameters,payoffs

ROOT=Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT);checks=[];records=[]
    def check(label,condition,**detail):checks.append(dict(check=label,passed=bool(condition),**detail))
    reference=json.loads(Path('configs/safeguarded_reference_sources.json').read_text())
    for path,sha in reference.items():check('pinned_source',hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path=path)
    base=yaml.safe_load(Path('configs/game.yaml').read_text());p=GameParameters(**base['parameters']).with_updates(**base['scenarios']['adaptation_negative'])
    for family,config_path,folder in [('linf','configs/safeguarded_game.yaml','outputs/scenario/safeguarded_game'),('rms','configs/safeguarded_game_rms.yaml','outputs/scenario/safeguarded_game_rms'),('coarse','configs/safeguarded_game_coarse.yaml','outputs/scenario/safeguarded_game_coarse')]:
        config=yaml.safe_load(Path(config_path).read_text())
        for kind,source in [('method','src/weaponized/game/safeguarded_iteration.py'),('runner','scripts/run_safeguarded_game.py')]:
            check('current_executed_snapshot',Path(folder,f'executed_{kind}_source.py').read_bytes()==Path(source).read_bytes(),family=family,kind=kind)
        for n in config['grids']:
            grid=StateGrid(n)
            for start in config['starts']:
                label=('coarse_' if config.get('warm_start_grid') else '')+start
                meta=Path(folder,f'adaptation_negative_n{n}_{label}.json');r=json.loads(meta.read_text());blob=Path(r['archive']).read_bytes()
                check('source_record',r['parameters']==asdict(p) and r['registry_sha256']==hashlib.sha256(Path(config_path).read_bytes()).hexdigest() and r['method_source_sha256']==reference['src/weaponized/game/safeguarded_iteration.py'],case=str(meta))
                check('saved_array_hash',hashlib.sha256(blob).hexdigest()==r['archive_sha256'],case=str(meta))
                with np.load(io.BytesIO(blob)) as z:
                    u,c,vu,vc=[z[k].ravel() for k in ['u','c','value_u','value_c']]
                    check('axes_and_domain',np.array_equal(z['axis'],grid.axes[0]) and all(len(a)==grid.count and np.isfinite(a).all() for a in [u,c,vu,vc]) and np.all((u>=0)&(u<=1)&(c>=0)&(c<=1)),case=str(meta))
                gen=build_generator(grid,p,u,c);rewards=payoffs(grid.states,u,c,p)
                residuals=[float(np.max(abs(rho*v-reward-gen@v))) for rho,v,reward in zip([p.rho_u,p.rho_c],[vu,vc],rewards)]
                gu,gc,bru,brc=policy_deviation_gaps(grid,p,[vu,vc],u,c)
                gain=float(max(gu.max(),gc.max()));action=float(max(np.max(abs(bru-u)),np.max(abs(brc-c))))
                accepted=gain<=1e-8 and action<=1e-7 and all(e<=1e-8*(1+np.max(abs(reward))) for e,reward in zip(residuals,rewards))
                check('original_global_acceptance_status',accepted==(r['status']=='verified_finite_grid_candidate') and r['continuous_mpe_certified'] is False,case=str(meta),gain=gain,action=action)
                if config.get('warm_start_grid'):
                    warm=Path(r['warm_start_archive']);payload=warm.read_bytes();h=hashlib.sha256(payload).hexdigest()
                    check('warm_start_hash',h==config['warm_start_archives'][start]==r['warm_start_archive_sha256'],case=str(meta))
                    small=StateGrid(config['warm_start_grid'])
                    with np.load(io.BytesIO(payload)) as z:
                        initial=[RegularGridInterpolator(small.axes,z[k].reshape(small.shape))(grid.states) for k in ['u','c']]
                else:initial=initial_policies(grid,start,config['seed'])
                values,_=evaluate_policies(grid,p,*initial)
                a,b,bu,bc=policy_deviation_gaps(grid,p,values,*initial)
                first=r['history'][0]
                check('initial_policy_reconstruction',np.isclose(max(a.max(),b.max()),first['max_deviation_gain'],rtol=1e-9,atol=1e-10) and np.isclose(max(np.max(abs(bu-initial[0])),np.max(abs(bc-initial[1]))),first['best_response_action_residual'],rtol=1e-9,atol=1e-10),case=str(meta))
                merit=[x['merit'] for x in r['history']]
                check('actual_search_merit_nonincreasing',all(b<=a+1e-12*(1+abs(a)) for a,b in zip(merit,merit[1:])),case=str(meta))
                records.append(dict(case=str(meta),accepted=bool(accepted),grid=n))
    result=dict(passed=all(x['passed'] for x in checks),checks=len(checks),attempts=len(records),accepted_coarse=sum(x['accepted'] and x['grid']==7 for x in records),accepted_fine=sum(x['accepted'] and x['grid']==17 for x in records),
                executed_at=datetime.now(timezone.utc).isoformat(),review_type='internal_independent_original_HJB_and_source_provenance_not_external_certification',
                failures=[x for x in checks if not x['passed']],checks_detail=checks,continuous_mpe_certified=False,floating_point_interval_certified=False)
    Path('outputs/diagnostics/safeguarded_independent_review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks_detail'},indent=2))
    return int(not result['passed'])


if __name__=='__main__':raise SystemExit(main())
