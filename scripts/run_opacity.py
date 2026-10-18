#!/usr/bin/env python
"""Run the evidence-gated Section 7 pipeline; no online acquisition during analysis."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
import pandas as pd
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from weaponized.opacity import spoi_daily, quarterly_spoi, aggregate_scores, opacity_regression_gate
from weaponized.opacity.coding import CODES
from weaponized.opacity.reliability import reliability_report
from weaponized.opacity.sensitivity import alternative_weights, window_sensitivity, factor_eligibility

ROOT=Path(__file__).resolve().parents[1]


def run(root=ROOT):
    root=Path(root)
    empirical=root/'outputs/empirical/opacity';synthetic=root/'outputs/synthetic/opacity'
    empirical.mkdir(parents=True,exist_ok=True);synthetic.mkdir(parents=True,exist_ok=True)
    settings=yaml.safe_load((root/'configs/opacity.yaml').read_text())
    data=root/'data/processed/opacity'
    obligations=pd.read_csv(data/'obligations.csv')
    events=pd.read_csv(data/'legal_events.csv')
    sources=pd.read_csv(data/'source_events.csv')
    daily=spoi_daily(obligations,events,sources,settings,'2025-01-01',settings['freeze'])
    quarters=quarterly_spoi(daily,settings['min_valid_quarter_days_fraction'])
    daily.to_csv(empirical/'daily_coverage.csv',index=False)
    quarters.to_csv(empirical/'quarterly_coverage.csv',index=False)
    sensitivities=window_sensitivity(obligations,events,sources,settings,'2025-01-01',settings['freeze'])
    sensitivities.to_csv(empirical/'window_sensitivity_coverage.csv',index=False)
    reliability=reliability_report([],[],independent=False)
    status={'evidence_class':'empirical_evidence_availability_audit',
            'freeze':settings['freeze'], 'days':len(daily),'observed_indicator_cells':int(daily[list(CODES)].notna().sum().sum()),
            'valid_days':int(daily.daily_valid.sum()),'valid_quarters':int(quarters.quarter_valid.sum()),
            'headline_spoi_status':'BLOCKED_NO_COVERAGE_VALID_INDEX_AND_NO_INDEPENDENT_CODING',
            'regression':opacity_regression_gate(quarters), 'intercoder_reliability':reliability,
            'factor_analysis':factor_eligibility(daily),
            'intent_inference':'not_identified; unavailable data are not evidence of deliberate nondisclosure',
            'legal_input_status':'candidate dates in blueprint are not admitted as verified primary observations'}
    (empirical/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    # Full-year quarter denominator, including unelapsed days in current partial quarter.
    # This documents availability rather than filling the unfinished quarter.
    fixtures=[]
    vectors={'opaque_illustrative':[1,2,4,4,1,3,1,2,2,3],
             'transparent_illustrative':[0,1,2,1,0,1,0,0,1,1]}
    for label,vector in vectors.items():
        scores=dict(zip(CODES,vector)); result=aggregate_scores(scores)
        fixtures.append({'fixture':label,'evidence_class':'fully_synthetic',**scores,**result,**alternative_weights(scores)})
    fixture_frame=pd.DataFrame(fixtures)
    fixture_frame.to_csv(synthetic/'blueprint_arithmetic.csv',index=False)
    fig,ax=plt.subplots(figsize=(6.4,3.6))
    ax.bar(['Illustrative vector A','Illustrative vector B'],fixture_frame.spoi,color=['#973b53','#387e9a'])
    ax.set(ylabel='SPOI (synthetic rubric arithmetic)',ylim=(0,100),title='SYNTHETIC — blueprint arithmetic verification')
    for i,value in enumerate(fixture_frame.spoi): ax.text(i,value+2,f'{value:.4f}',ha='center')
    fig.tight_layout();fig.savefig(synthetic/'blueprint_arithmetic.png',dpi=200);fig.savefig(synthetic/'blueprint_arithmetic.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
    files=[root/'configs/opacity.yaml',root/'codebooks/spoi_codebook.csv', root/'metadata/opacity_sources.csv',
           root/'docs/opacity_evidence.md',Path(__file__),root/'tests/test_opacity.py',
           *(root/'src/weaponized/opacity').glob('*.py'),*data.glob('*.csv'),*empirical.glob('*'),*synthetic.glob('*')]
    files=sorted(p for p in files if p.name != 'module_manifest.json')
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    (empirical/'module_manifest.json').write_text(json.dumps({'command':'.venv/bin/python scripts/run_opacity.py','freeze':settings['freeze'],'python_version':sys.version,
        'inputs_and_outputs_sha256':hashes,'synthetic_outputs_separate':True},indent=2)+'\n')
    print(json.dumps({k:status[k] for k in ('days','valid_days','valid_quarters','headline_spoi_status')}))
    return status

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(ROOT));args=parser.parse_args();run(args.root)
