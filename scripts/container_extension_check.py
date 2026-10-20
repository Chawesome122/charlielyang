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
        "data/processed/rare_earths/activity_discovery_registry.csv",
        "data/processed/rare_earths_additional/lynas_project_history.csv",
        "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv",
        "data/processed/rare_earths_additional/lynas_quarterly_annual_reconciliation.csv",
        "outputs/empirical/rare_earths/lynas_quarterly_baseline_predictions.csv",
        "outputs/empirical/rare_earths/lynas_quarterly_baseline_scores.csv",
        "data/processed/industrial_evidence/project_milestones.csv",
        "data/processed/industrial_evidence/technical_claims.csv",
        "data/processed/industrial_evidence/activity_coverage.csv",
        "outputs/empirical/rare_earths/evidence_coverage_by_stage.csv",
        "outputs/empirical/rare_earths/finite_batch_evidence.json",
        "data/processed/semiconductors/legal_events.csv",
        "data/processed/semiconductors/legal_discovery_screening.csv",
        "data/processed/industrial_evidence/mp_cash_ppe_versions.csv",
        "outputs/empirical/rare_earths/mp_halfyear_cash_ppe.csv",
        "data/processed/project_histories/milestone_versions.csv",
        "data/processed/project_histories/state_observations.csv",
        "data/processed/project_histories/milestone_revision_audit.csv",
        "data/processed/project_histories/latest_visible_milestones.csv",
        "data/processed/project_histories/state_pair_audit.csv",
        "data/processed/project_histories/quarterly_disclosure_inventory.csv",
        "data/processed/finance_material/publication_clock_audit.csv",
        "data/processed/finance_material/observations.csv",
        "data/processed/finance_material/prospective_product_comparisons.csv",
        "data/processed/engineering_inputs/observations.csv",
        "data/processed/engineering_inputs/conditional_oxide_constraints.csv",
        "data/processed/engineering_inputs/recovery_assumption_versions.csv",
        "data/processed/publication_extension/annual_clock_blockers.csv",
        "data/processed/publication_extension/rejected_date_candidates.csv",
        "data/processed/publication_extension/source_origin_readiness.csv",
        "data/processed/publication_extension/claim_origin_masking.csv",
        "data/processed/legal_provisions/provisions.csv",
        "data/processed/legal_provisions/quoted_elements.csv",
        "data/processed/legal_provisions/technical_bounds.csv",
        "data/processed/legal_provisions/amendment_links.csv",
        "data/processed/legal_provisions/issued_phase_checks.csv",
        "data/processed/source_integrity/original_quote_audit.csv",
        "data/processed/mp_measurement/native_cell_versions.csv",
        "data/processed/mp_measurement/definitions.csv",
        "data/processed/mp_measurement/quarter_annual_reconciliation.csv",
        "data/processed/mp_measurement/currency_inventory_identities.csv",
        "data/processed/mp_measurement/comparative_vintage_audit.csv",
        "data/processed/mp_measurement/production_sales_comparisons.csv",
        "data/processed/mp_measurement/annual_asof_freeze.csv",
        "outputs/empirical/rare_earths/mp_quarterly_baseline_predictions.csv",
        "outputs/empirical/rare_earths/mp_quarterly_baseline_scores.csv",
        "outputs/empirical/rare_earths/mp_quarterly_origin_audit.csv",
        "manuscript/mp_baselines.tex",
        "data/processed/white_mesa/observations.csv",
        "data/processed/white_mesa/reported_flow_ratios.csv",
        "data/processed/white_mesa/stock_origin_audit.csv",
        "data/processed/white_mesa/capacity_component_identities.csv",
        "data/processed/white_mesa/product_form_versions.csv",
        "data/processed/white_mesa/basis_corrections.csv",
        "data/processed/rare_earths/observations.csv",
        "data/processed/rare_earths/observations_asof_freeze.csv",
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
    current = json.loads((ROOT/"outputs/research_summary.json").read_text())
    report["test_results"] = {key:current[key] for key in ["tests", "test_failures"]}
    report["extension_scope"] = "MP native production/sales and monetary inventories, source definitions, missing-state/reconciliation audit and descriptive quarterly baselines; existing White Mesa, original-source, engineering/legal and scenario pipeline"
    report["executed_script_sha256"] = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted((ROOT/"scripts").glob("*.py"))}
    (ROOT/"outputs/diagnostics/container_extension_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
