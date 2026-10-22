#!/usr/bin/env python3
"""Offline end-to-end replication, failing on any unexpected command error.

Default regenerates empirical extracts, mathematical validation, 10,000 synthetic
paths and manuscript, and independently verifies saved large-grid game arrays.
--full recomputes large-grid policies and registered scenario comparisons too.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    for key in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[key] = "1"
    os.environ.setdefault("SOURCE_DATE_EPOCH", "1792281600")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
    commands = [
        ["scripts/build_rare_earths.py"],
        ["scripts/resolve_publication_clocks.py"],
        ["scripts/build_finance_material.py"], ["scripts/build_white_mesa.py"], ["scripts/build_mp_measurement.py"],
        ["scripts/build_operating_origin_extension.py"], ["scripts/analyze_operating_origin_extension.py"], ["scripts/review_operating_origin_independent.py"],
        ["scripts/build_publication_extension.py"], ["scripts/build_engineering_inputs.py"],
        ["scripts/fetch_additional_rare_earths.py"],
        ["scripts/build_lynas_history.py"], ["scripts/build_lynas_revisions.py"],
        ["scripts/build_industrial_evidence.py"],
        ["scripts/build_project_histories.py"],
        ["scripts/build_mp_investment.py"],
        ["scripts/build_project_registry.py"],
        ["scripts/audit_project_observations.py"],
        ["scripts/build_evidence_coverage.py"],
        ["scripts/build_citation_audit.py"], ["scripts/run_semiconductors.py"],
        ["scripts/build_smic_operations.py"], ["scripts/analyze_smic_operations.py"],
        ["scripts/discover_legal.py"], ["scripts/review_legal_discovery.py"], ["scripts/build_legal_provisions.py"],
        ["scripts/build_entity_schedules.py"], ["scripts/analyze_entity_schedules.py"],
        ["scripts/build_veu_extension.py"], ["scripts/analyze_veu_extension.py"], ["scripts/review_veu_independent.py"], ["scripts/build_source_requests.py"],
        ["scripts/run_opacity.py"], ["scripts/run_physical.py"],
        ["scripts/run_forecast.py", "--draws", "10000"],
        ["scripts/run_empirical_baselines.py"],
        ["scripts/run_lynas_baselines.py"], ["scripts/analyze_mp_measurement.py"],
        ["scripts/run_constant_controls.py"],
    ]
    if args.full:
        commands += [
            ["scripts/run_game.py", "--grids", "5", "7", "--scenarios", "adaptation_positive"],
            ["scripts/run_game.py", "--grids", "17", "21", "--max-iterations", "120", "--scenarios", "adaptation_positive"],
            ["scripts/run_game.py", "--grids", "17", "21", "--starts", "mid", "--scenarios", "adaptation_negative", "adaptation_zero"],
            ["scripts/run_game.py", "--grids", "17", "--starts", "mid", "--scenarios", "adaptation_negative", "--method", "alternating", "--max-iterations", "60", "--out", "outputs/scenario/game/alternate_attempt"],
            ["scripts/run_game.py", "--grids", "7", "--starts", "mid", "--scenarios", "adaptation_negative", "adaptation_zero", "patient", "impatient", "substitution", "complementarity", "industrial_subsidy_growth", "foreign_licensing_relaxation"],
        ]
    if args.full:
        import yaml
        registry = yaml.safe_load((ROOT/"configs/negative_beta_extension.yaml").read_text())
        commands.append(registry["command"])
        commands += [["scripts/run_safeguarded_game.py", "--registry", "configs/safeguarded_game.yaml", "--out", "outputs/scenario/safeguarded_game"],
                     ["scripts/run_safeguarded_game.py", "--registry", "configs/safeguarded_game_rms.yaml", "--out", "outputs/scenario/safeguarded_game_rms"],
                     ["scripts/run_safeguarded_game.py", "--registry", "configs/safeguarded_game_coarse.yaml", "--out", "outputs/scenario/safeguarded_game_coarse"]]
    commands += [["scripts/audit_game.py", "--out", folder] for folder in ["outputs/scenario/safeguarded_game","outputs/scenario/safeguarded_game_rms","outputs/scenario/safeguarded_game_coarse"]]
    commands += [["scripts/analyze_safeguarded_game.py"], ["scripts/review_safeguarded_independent.py"], ["scripts/audit_game.py", "--out", "outputs/scenario/negative_beta_extension"],
                 ["scripts/analyze_negative_extension.py"], ["scripts/audit_original_quotes.py"], ["scripts/plot_evidence_extensions.py"], ["scripts/plot_white_mesa.py"],
                 ["scripts/audit_game.py"], ["scripts/run_dynamic_deviation_audit.py"], ["scripts/validate.py"], ["-m", "pytest", "-q", "--junitxml=outputs/diagnostics/pytest.xml"],
                 ["scripts/report.py"]]
    steps = []
    start = time.monotonic()
    logdir = ROOT/"outputs/diagnostics/replication_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    for i, command in enumerate(commands):
        logpath = logdir/f"{i:02d}_{Path(command[0]).stem}.log"
        stamp = time.monotonic()
        print("RUN", " ".join(command), flush=True)
        with logpath.open("w") as log:
            result = subprocess.run([sys.executable, *command], stdout=log, stderr=subprocess.STDOUT)
        steps.append(dict(command=command, exit_code=result.returncode,
                          seconds=time.monotonic()-stamp, log=str(logpath.relative_to(ROOT))))
        if result.returncode:
            print(logpath.read_text()[-6000:], file=sys.stderr)
            break
    passed = all(step["exit_code"] == 0 for step in steps) and len(steps) == len(commands)
    if passed and not args.no_pdf:
        from weaponized.reporting.latex import build_manuscript
        build = build_manuscript(ROOT)
        logpath = logdir/"manuscript.log"
        steps.append(dict(command=["latexmk", "main.tex", "then_verified_convergent_pdflatex"], exit_code=int(not build["passed"]),
                          log=str(logpath.relative_to(ROOT))))
        passed &= build["passed"]
        if not build["passed"]:
            print(logpath.read_text()[-6000:], file=sys.stderr)
    summary = dict(passed=passed, scope="full_recomputation" if args.full else "rebuild_plus_independent_saved_game_verification",
                   freeze="2026-10-11", network_required=False, steps=steps,
                   total_seconds=time.monotonic()-start,
                   independent_machine=False,
                   note="Expected negative-beta nonconvergence is a scientific result recorded by successful scripts, not a passing equilibrium.")
    (ROOT/"outputs/diagnostics/end_to_end_replication.json").write_text(json.dumps(summary, indent=2))
    # Capture final output state after PDF and execution evidence exist.
    if passed:
        subprocess.run([sys.executable, "scripts/update_status.py"], check=True)
        subprocess.run([sys.executable, "scripts/report.py", "--manifest-only"], check=True)
    print(json.dumps({k:v for k,v in summary.items() if k != "steps"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
