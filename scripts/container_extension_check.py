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
        "data/processed/entity_schedules/entries.csv",
        "data/processed/entity_schedules/source_rows.csv",
        "data/processed/entity_schedules/table_notes.csv",
        "data/processed/entity_schedules/amendatory_instructions.csv",
        "data/processed/entity_schedules/source_clocks.csv",
        "data/processed/entity_schedules/publication_vintage_checks.csv",
        "outputs/empirical/semiconductors/entity_review_counts.csv",
        "outputs/empirical/semiconductors/entity_source_quality_flags.csv",
        "outputs/empirical/semiconductors/entity_schedule_summary_table.csv",
        "manuscript/entity_schedules_table.tex",
        "data/processed/smic_operations/observations.csv",
        "data/processed/smic_operations/observations_asof_freeze.csv",
        "data/processed/smic_operations/source_clocks.csv",
        "data/processed/smic_operations/definitions.csv",
        "data/processed/smic_operations/revenue_share_identities.csv",
        "data/processed/smic_operations/capacity_presentation_audit.csv",
        "data/processed/smic_operations/comparative_vintages.csv",
        "outputs/empirical/semiconductors/smic_wafer_revenue_ratios.csv",
        "outputs/empirical/semiconductors/smic_revenue_decompositions.csv",
        "manuscript/smic_operating_changes.tex",
        "data/processed/semiconductors/reported_financial_inputs.csv",
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
    paths += ['outputs/scenario/negative_beta_extension/registered_attempts.csv', 'outputs/scenario/negative_beta_extension/largest_action_residual_nodes.csv', 'outputs/scenario/negative_beta_extension/iteration_history.csv', 'manuscript/negative_extension_table.tex', 'outputs/scenario/constant_controls/equilibria.csv', 'outputs/scenario/constant_controls/initializations.csv', 'outputs/scenario/constant_controls/unilateral_deviations.csv', 'outputs/scenario/constant_controls/validation.csv', 'outputs/scenario/constant_controls/full_payoff_crosschecks.csv', 'manuscript/constant_controls_table.tex']
    paths += ['data/processed/operating_origin_extension/observations.csv', 'data/processed/operating_origin_extension/procurement_comparative_versions.csv', 'data/processed/operating_origin_extension/reported_equity_closure.csv', 'data/processed/operating_origin_extension/publication_vintage_checks.csv', 'data/processed/operating_origin_extension/route_evidence_admission.csv', 'outputs/empirical/rare_earths/operating_origin_extension/event_clock_table.csv', 'manuscript/operating_origin_extension_table.tex', 'data/processed/veu_extension/clauses.csv', 'data/processed/veu_extension/issued_events.csv', 'data/processed/veu_extension/source_clocks.csv', 'data/processed/veu_extension/permission_removal_links.csv', 'data/processed/veu_extension/origin_phase_checks.csv', 'outputs/empirical/semiconductors/veu_extension/scope_summary.csv', 'outputs/empirical/semiconductors/veu_extension/scope_table.tex', 'outputs/scenario/dynamic_deviation_audit/value_bounds.csv', 'outputs/scenario/dynamic_deviation_audit/source_archives.csv', 'outputs/scenario/dynamic_deviation_audit/policy_iteration_history.csv', 'outputs/scenario/dynamic_deviation_audit/diagnostic_states.csv', 'outputs/scenario/dynamic_deviation_audit/table.tex', 'metadata/priority_source_requests.csv', 'docs/INPUTS_NEEDED.md']
    paths += ['outputs/scenario/safeguarded_analysis/attempts.csv', 'outputs/scenario/safeguarded_analysis/iteration_history.csv', 'outputs/scenario/safeguarded_analysis/archive_integrity.csv', 'outputs/scenario/safeguarded_analysis/summary_table.csv', 'outputs/scenario/safeguarded_analysis/scenario_table.tex']
    paths += [f'data/processed/supplied_evidence/{name}.csv' for name in ['source_admissions','claims','smic_quarterly_versions','legal_pdf_correspondence','smic_comparative_versions','publication_origin_checks','event_definition_windows']]
    paths += [f'outputs/empirical/supplied_evidence/{name}.csv' for name in ['white_mesa_design_versions','vara_conditional_oxide_composition','smic_revenue_ratios','smic_accounting_decompositions','numerical_checks']]
    paths += ['manuscript/supplied_smic_changes.tex','outputs/empirical/supplied_evidence/analysis.json']
    paths += ['outputs/empirical/supplied_evidence/smic_guidance_evaluation.csv','outputs/empirical/supplied_evidence/guidance_analysis.json']
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
    report["extension_scope"] = "MP operating origin/ownership/routing and VEU facility/item permissions/removals; independently recomputed fixed-opponent dynamic deviations and request readiness; " + "Nine reciprocal constant-commitment scenario solves with analytic bounds and exact/full-payoff checks; three additional saved 17^4 negative-beta failures independently re-audited; nine Entity List original schedules: printed party/address versions, exact review conditions, source notes/instructions, filing/effective/publication clocks and XML quality flags; prior SMIC, MP, White Mesa, engineering/legal, vintage and scenario modules"
    report["executed_script_sha256"] = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted((ROOT/"scripts").glob("*.py"))}
    (ROOT/"outputs/diagnostics/container_extension_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
