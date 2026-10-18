"""Verify continuation extraction and reporting in a disconnected clean image.

Large games are independently re-audited, not re-solved. The separately retained
earlier full-container run applies to unchanged numerical core code only.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [
        "data/processed/rare_earths/project_state_evidence.csv",
        "data/processed/rare_earths_additional/lynas_project_history.csv",
        "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv",
        "data/processed/rare_earths_additional/lynas_quarterly_annual_reconciliation.csv",
        "outputs/empirical/rare_earths/lynas_quarterly_baseline_predictions.csv",
        "outputs/empirical/rare_earths/lynas_quarterly_baseline_scores.csv",
    ]
    before = {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in paths}
    run = subprocess.run([sys.executable, "scripts/replicate.py"], cwd=ROOT)
    checks = [dict(path=path, passed=hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest)
              for path, digest in before.items()]
    report = dict(passed=run.returncode == 0 and all(row["passed"] for row in checks),
                  scope="clean_container_continuation_rebuild_and_saved_game_audit",
                  network="none", independent_machine=False, pipeline_exit_code=run.returncode,
                  tables_byte_identity=checks, large_games_recomputed=False,
                  full_prior_numerical_run="outputs/diagnostics/container_validation.json",
                  current_numerical_core_comparison="outputs/diagnostics/scientific_code_comparison.json")
    (ROOT/"outputs/diagnostics/container_extension_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
