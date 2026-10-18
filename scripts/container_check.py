"""Fresh disconnected container recomputation against supplied scientific outputs.

Baseline arrays are retained in memory before recomputation; all large policies
are then solved again. Timing/TeX metadata are excluded from scientific equality.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    tables=["data/processed/rare_earths/observations_asof_freeze.csv",
            "data/processed/rare_earths_additional/lynas_annual_production.csv",
            "data/processed/semiconductors/reported_financial_inputs.csv",
            "outputs/empirical/rare_earths/baseline_scores.csv"]
    hashes={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in tables}
    gamepaths=["adaptation_positive_n17_zero.npz","adaptation_positive_n21_zero.npz","adaptation_zero_n21_mid.npz"]
    expected={}
    for name in gamepaths:
        with np.load(ROOT/"outputs/scenario/game"/name) as data:
            expected[name]={key:data[key].copy() for key in ["u","c","value_u","value_c"]}
    previous=json.loads((ROOT/"outputs/research_summary.json").read_text())
    run=subprocess.run([sys.executable,str(ROOT/"scripts/replicate.py"),"--full"],cwd=ROOT)
    checks=[]
    if run.returncode==0:
        for path,digest in hashes.items():
            actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            checks.append(dict(kind="source_derived_table_byte_identity",path=path,passed=actual==digest))
        for name,fields in expected.items():
            with np.load(ROOT/"outputs/scenario/game"/name) as data:
                for key,array in fields.items():
                    difference=float(np.max(abs(data[key]-array)))
                    checks.append(dict(kind="recomputed_game_array",path=name,field=key,
                                       max_absolute_difference=difference,tolerance=1e-6,passed=difference<=1e-6))
        current=json.loads((ROOT/"outputs/research_summary.json").read_text())
        for key in ["rare_earth_versioned_observations","lynas_annual_observations","legal_event_rows","financial_input_rows","finite_grid_candidate_runs","not_solved_runs","test_failures"]:
            checks.append(dict(kind="scientific_summary",field=key,expected=previous[key],actual=current[key],passed=previous[key]==current[key]))
    passed=run.returncode==0 and bool(checks) and all(item["passed"] for item in checks)
    report=dict(passed=passed,scope="clean_container_full_recomputation",network="none",
                pipeline_exit_code=run.returncode,checks=checks,independent_machine=False,
                float_comparison_note="1e-6 absolute tolerance for separately recomputed approximate finite-grid values/policies; empirical table bytes must match exactly",
                source_base_image="python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e")
    (ROOT/"outputs/diagnostics/container_validation.json").write_text(json.dumps(report,indent=2))
    if passed:
        subprocess.run([sys.executable,"scripts/update_status.py"],cwd=ROOT,check=True)
        subprocess.run([sys.executable,"scripts/report.py","--manifest-only"],cwd=ROOT,check=True)
    print(json.dumps(report,indent=2),flush=True)
    return 0 if passed else 1


if __name__=="__main__":raise SystemExit(main())
