"""Validate actual archived observations and keep evidence gaps distinct from errors."""
import json
from pathlib import Path
import pandas as pd
import re
import subprocess
from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text
from weaponized.io.publication import linked_publication_clock
from weaponized.io.schemas import Claim

ROOT=Path(__file__).resolve().parents[1]


def main():
    failures=[];checks=0
    observations=pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv").replace({float('nan'):None})
    sources=json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in observations.to_dict("records"):
        try:
            Claim(**{key:row.get(key) for key in Claim.model_fields})
            assert sha256_file(ROOT/sources[row["source_id"]]["archive_path"])==row["source_sha256"]
            checks+=1
        except Exception as error:
            failures.append(f"{row.get('record_version_id')}: {type(error).__name__}: {error}")
    for file,pathcol in [("metadata/semiconductor_sources.csv","path"),("metadata/additional_rare_earth_sources.csv","archive_path"),("metadata/literature_sources.csv","path"),("metadata/literature_sources_additional.csv","path")]:
        data=pd.read_csv(ROOT/file)
        for row in data.to_dict("records"):
            if not isinstance(row.get(pathcol),str) or not isinstance(row.get("sha256"),str):continue
            checks+=1
            if sha256_file(ROOT/row[pathcol])!=row["sha256"]:failures.append(f"Artifact hash mismatch:{row[pathcol]}")
    for file in ["data/processed/rare_earths_additional/lynas_annual_production.csv","data/processed/semiconductors/reported_financial_inputs.csv","data/processed/semiconductors/legal_events.csv"]:
        data=pd.read_csv(ROOT/file)
        checks+=1
        if not (data.info_public_date.notna() & data.info_public_date.le("2026-10-11")).all():failures.append(f"Source cutoff/missing clock:{file}")
    discovery=ROOT/"metadata/legal_discovery_acquisitions.jsonl"
    if discovery.exists():
        unique={}
        for line in discovery.read_text().splitlines():
            row=json.loads(line)
            if row['status']=='downloaded':unique[(row['archive_path'],row['sha256'])]=row
        for (path,digest),row in unique.items():
            checks+=1
            if sha256_file(ROOT/path)!=digest:failures.append(f"Discovery artifact hash mismatch:{path}")
            if row.get('publication_date') and row['publication_date']>'2026-10-11':failures.append(f"Future discovery document:{row['source_id']}")
    revision=ROOT/"data/processed/rare_earths_additional/lynas_observed_revisions.csv"
    if revision.exists():
        rows=pd.read_csv(revision)
        checks+=1
        if not (rows.info_public_date.le('2026-10-11')).all():failures.append('Future Lynas revision admitted')
    additional = pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").set_index("source_id")
    for filename in ["lynas_project_history.csv", "lynas_quarterly_production_versions.csv", "lynas_documented_material_links.csv"]:
        data = pd.read_csv(ROOT/"data/processed/rare_earths_additional"/filename).fillna("")
        for row in data.to_dict("records"):
            checks += 1
            source = additional.loc[row["source_id"]]
            if row["source_sha256"] != source.sha256 or sha256_file(ROOT/source.archive_path) != source.sha256:
                failures.append(f"Lynas claim/source hash mismatch:{filename}")
            if not row["info_public_date"] or row["info_public_date"] > "2026-10-11":
                failures.append(f"Lynas historical clock missing/future:{filename}")
            if filename == "lynas_project_history.csv":
                page = verified_original_text(ROOT/source.archive_path, source.sha256).split("\f")[int(row["pdf_page"])-1]
                if row["quote"] not in " ".join(page.split()):
                    failures.append(f"Lynas milestone quote mismatch:{row['claim_id']}")
    reconcile = pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_quarterly_annual_reconciliation.csv")
    checks += len(reconcile)
    if not reconcile.difference.eq(0).all():failures.append("Lynas quarterly/annual production mismatch")
    for filename in ["project_milestones.csv", "technical_claims.csv"]:
        data = pd.read_csv(ROOT/"data/processed/industrial_evidence"/filename).fillna("")
        for row in data.to_dict("records"):
            checks += 1
            source = sources.get(row["source_id"])
            if source is None:
                source = additional.loc[row["source_id"]].to_dict()
            if row["source_sha256"] != source["sha256"] or sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
                failures.append(f"Industrial evidence source mismatch:{row.get('record_id', row.get('observation_id'))}")
            if not row["info_public_date"] or row["info_public_date"] > "2026-10-11":
                failures.append("Industrial evidence source-public clock missing/future")
            if filename == "technical_claims.csv":
                try:
                    Claim(**{key:(None if row.get(key) == "" else row.get(key)) for key in Claim.model_fields})
                except Exception as error:
                    failures.append(f"Industrial claim schema:{row['observation_id']}:{error}")
    screenings = pd.read_csv(ROOT/"data/processed/semiconductors/legal_discovery_screening.csv")
    checks += len(screenings)
    if not screenings.info_public_date.le("2026-10-11").all():failures.append("Future legal scope screen")
    cash_source=sources["RE-MP-FACTS"]
    cash_payload=json.loads((ROOT/cash_source["archive_path"]).read_text())
    tag="PaymentsToAcquirePropertyPlantAndEquipment"
    cash=pd.read_csv(ROOT/"data/processed/industrial_evidence/mp_cash_ppe_versions.csv").replace({float('nan'):None})
    for row in cash.to_dict("records"):
        checks+=1
        fact=cash_payload["facts"]["us-gaap"][tag]["units"]["USD"][int(row["source_array_index"])]
        try:
            Claim(**{key:row.get(key) for key in Claim.model_fields})
            assert row["source_sha256"]==cash_source["sha256"]
            assert row["period_start"]==fact["start"] and row["period_end"]==fact["end"]
            assert row["value"]==fact["val"] and row["info_public_date"]==fact["filed"]
            assert row["info_public_date"]<="2026-10-11"
        except Exception as error:
            failures.append(f"Cash PPE fact provenance:{row['record_version_id']}:{error}")
    histories=pd.read_csv(ROOT/"data/processed/project_histories/milestone_versions.csv").fillna("")
    for row in histories.to_dict("records"):
        checks+=1
        source=sources[row["source_id"]]
        text=" ".join(verified_original_text(ROOT/source["archive_path"], source["sha256"]).split())
        if row["source_sha256"]!=source["sha256"] or sha256_file(ROOT/source["archive_path"])!=source["sha256"]:
            failures.append(f"Project history source mismatch:{row['record_id']}")
        if row["quote"] not in text or row["info_public_date"]!=source["publication_date"] or row["info_public_date"]>"2026-10-11":
            failures.append(f"Project history quote/public clock mismatch:{row['record_id']}")
    inventory=pd.read_csv(ROOT/"data/processed/project_histories/quarterly_disclosure_inventory.csv")
    checks+=1
    if not inventory.origin_date.le("2026-10-11").all() or inventory.physical_projects_at_risk.notna().any() or inventory.known_survival_exposure_quarters.notna().any():
        failures.append("Disclosure inventory mislabeled as physical survival exposure or future origin")
    roster=pd.read_csv(ROOT/"data/processed/rare_earths/activity_discovery_registry.csv")
    checks+=1
    if "archive_first_documented_public_date" not in roster:
        failures.append("Discovery roster lacks earliest archive-public clock")
    else:
        upton=roster[roster.activity_id.eq("RER_Upton_separation")]
        if len(upton)!=1 or upton.iloc[0].archive_first_documented_public_date!="2024-03-20":
            failures.append("Upton discovery chronology ignores an earlier verified filing")
    clocks=pd.read_csv(ROOT/"data/processed/finance_material/publication_clock_audit.csv").fillna("")
    for row in clocks.to_dict("records"):
        checks+=1
        source,clock=sources[row["source_id"]],sources[row["public_clock_source_id"]]
        if sha256_file(ROOT/source["archive_path"])!=row["source_sha256"] or sha256_file(ROOT/clock["archive_path"])!=row["public_clock_source_sha256"]:
            failures.append("Publication-clock/report source mismatch")
        try:
            result=linked_publication_clock((ROOT/clock["archive_path"]).read_text(),clock["url"],source["url"],row["method"])
        except ValueError:
            if row["status"]!="UNRESOLVED" or row["info_public_date"] or source.get("publication_date"):
                failures.append("Unresolved public clock silently assigned a date")
        else:
            if row["status"]!="RESOLVED" or row["info_public_date"]!=result["info_public_date"] or source["publication_date"]!=result["info_public_date"]:
                failures.append("Publication clock failed exact-link revalidation")
    finance=pd.read_csv(ROOT/"data/processed/finance_material/observations.csv").fillna("")
    pdfs={}
    for row in finance.to_dict("records"):
        checks+=1
        source=sources[row["source_id"]]
        if row["source_id"] not in pdfs:
            text=subprocess.check_output(["pdftotext","-layout",str(ROOT/source["archive_path"]),"-"],text=True)
            pdfs[row["source_id"]]=[" ".join(p.split()) for p in text.split("\f")]
        page=pdfs[row["source_id"]][int(row["pdf_page"])-1]
        if row["quote"] not in page or row["source_sha256"]!=source["sha256"] or row["info_public_date"]!=source["publication_date"] or row["public_clock_source_sha256"]!=source["public_clock_source_sha256"]:
            failures.append(f"Finance/material provenance mismatch:{row['claim_id']}")
        if row["value_type"]=="number":
            numbers=[float(n.replace(",","")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?",row["quote"])]
            numeric=float(row["value"])
            if abs(numeric) not in numbers and not (row["variable"]=="contract_initial_term" and numeric==4 and "four years" in row["quote"]):
                failures.append(f"Finance/material numerical support absent:{row['claim_id']}")
        try:
            Claim(**{key:(None if row.get(key)=="" else row.get(key)) for key in Claim.model_fields})
        except Exception as error:
            failures.append(f"Finance/material claim schema:{row['claim_id']}:{error}")
    for diagnostic, count_fields in [
        ("original_quote_validation.json", ["checks"]),
        ("operating_origin_extension_validation.json", ["source_claims","equity_closure_checks","procurement_comparative_groups","publication_origins","route_admission_cases"]),
        ("veu_extension_validation.json", ["primary_quote_checks","rule_clock_checks","link_checks","origin_phase_checks"]),
        ("source_request_readiness.json", ["immutable_submission_pointer_checks"]),
        ("supplied_evidence_validation.json", ["source_identity_clock_checks","claims","smic_native_cells","legal_pdf_checks"]),
        ("mp_measurement_validation.json", ["native_cell_versions", "definition_claims", "numeric_quarter_annual_identities", "currency_inventory_identities"]),
        ("smic_operations_validation.json", ["source_claims", "verified_source_clocks", "definition_claims", "revenue_share_identities", "capacity_presentation_checks", "existing_R_and_D_crosschecks"]),
        ("entity_schedules_validation.json", ["printed_entry_versions", "original_table_rows", "table_notes", "amendatory_instructions", "source_clock_checks", "vintage_checks", "entry_action_crosswalk_records"]),
        ("white_mesa_validation.json", ["source_claims", "stock_origin_checks", "capacity_component_checks", "product_form_origin_checks", "legacy_basis_corrections"]),
        ("engineering_inputs_validation.json", ["source_claims", "normalized_finite_feed_LP_checks"]),
        ("legal_provisions_validation.json", ["exact_quoted_elements", "exact_dates_elements", "source_artifacts"]),
        ("publication_extension_validation.json", ["source_origin_pairs", "origin_mask_checks", "rejected_auxiliary_date_candidates"]),
    ]:
        report=json.loads((ROOT/"outputs/diagnostics"/diagnostic).read_text())
        checks += sum(report[key] for key in count_fields)
        if not report["passed"]:failures.append(f"Extension validation failed:{diagnostic}")
    mp_predictions=pd.read_csv(ROOT/"outputs/empirical/rare_earths/mp_quarterly_baseline_predictions.csv")
    checks+=len(mp_predictions)
    if not (mp_predictions.max_training_public_date.le(mp_predictions.origin) & mp_predictions.max_training_period_end.le(mp_predictions.origin) & mp_predictions.target.gt(mp_predictions.origin) & mp_predictions.outcome_public_date.le("2026-10-11")).all():
        failures.append("MP producer hindcast information leakage")
    smic=json.loads((ROOT/"outputs/empirical/semiconductors/smic_operations_analysis.json").read_text())
    supplied=json.loads((ROOT/'outputs/empirical/supplied_evidence/analysis.json').read_text())
    checks+=supplied['numerical_checks']+supplied['vintage_checks']
    if not supplied['passed'] or any(supplied[k] for k in ['empirical_service_identified','causal_effect_estimated','forecast_probabilities_produced','source_bytes_at_freeze_certified']):
        failures.append('Supplied evidence validation or scientific-claim boundary failed')
    guidance=json.loads((ROOT/'outputs/empirical/supplied_evidence/guidance_analysis.json').read_text())
    checks+=guidance['related_outcomes']
    if not guidance['passed'] or guidance['statistical_skill_established'] or guidance['interval_probability_coverage_claimed'] or guidance['empirical_magnet_service_forecast']:
        failures.append('Issuer guidance timing or scientific-label guard failed')
    checks+=smic["accounting_decompositions"]
    if not smic["passed"] or smic["causal_effect_identified"] or smic["advanced_node_or_domestic_tool_capability_identified"] or smic["foreign_access_identified"]:
        failures.append("SMIC descriptive accounting mislabeled as causal/target-capability evidence or failed identity")
    entity=json.loads((ROOT/"outputs/empirical/semiconductors/entity_schedules_analysis.json").read_text())
    if not entity["passed"] or entity["foreign_access_or_causal_effect_identified"] or entity["current_law_consolidated"] or entity["source_flags_measure_policy_opacity"]:
        failures.append("Entity schedules mislabeled as access/causal, consolidated-law or policy-opacity evidence")
    commitment=json.loads((ROOT/"outputs/scenario/constant_controls/analysis.json").read_text())
    checks+=sum(commitment[k] for k in ["certificate_checks","start_checks","deviation_profile_points","exact_zero_beta_checks","full_payoff_crosschecks","quadrature_refinement_checks"])
    if not commitment["passed"] or commitment["full_feedback_mpe_certified"] or commitment["unrestricted_open_loop_equilibrium_certified"] or commitment["empirical_calibration"] or commitment["numerical_ODE_interval_certified"]:
        failures.append("Constant commitment benchmark failed or has an invalid stronger label")
    negative=json.loads((ROOT/"outputs/scenario/negative_beta_extension/analysis.json").read_text())
    checks+=negative["registered_attempts"]
    if not negative["passed"] or negative["continuous_mpe_certified"] or negative["nonexistence_proved"] or negative["parameters_empirically_identified"]:
        failures.append("Additional negative-beta archives/status failed or have an invalid stronger label")
    origin=json.loads((ROOT/"outputs/diagnostics/operating_origin_extension_validation.json").read_text())
    if origin["empirical_China_free_service_identified"] or origin["causal_policy_effect_identified"] or origin["full_route_data_admitted"]:
        failures.append("Commercial origin disclosures promoted to complete service or causal evidence")
    veu=json.loads((ROOT/"outputs/diagnostics/veu_extension_validation.json").read_text())
    if veu["current_law_consolidation_verified"] or veu["foreign_access_identified"] or veu["actual_license_outcome_observed"]:
        failures.append("VEU permission/removal text promoted to current law or measured access")
    dynamic=json.loads((ROOT/"outputs/scenario/dynamic_deviation_audit/analysis.json").read_text())
    checks+=sum(dynamic[k] for k in ["source_array_checks","unilateral_policy_audits","fixed_opponent_checks","finite_state_bound_checks"])
    if not dynamic["passed"] or dynamic["continuous_mpe_certified"] or dynamic["floating_point_interval_certified"] or dynamic["empirical_calibration"] or dynamic["full_game_nash_promoted_by_this_audit"]:
        failures.append("Dynamic-deviation numerical audit failed or promoted beyond its finite-state scope")
    safeguarded=json.loads((ROOT/"outputs/scenario/safeguarded_analysis/analysis.json").read_text())
    checks+=safeguarded["archive_integrity_checks"]+safeguarded["reference_source_checks"]
    if not safeguarded["passed"] or safeguarded["continuous_mpe_certified"] or safeguarded["nonexistence_proved"] or safeguarded["thresholds_relaxed"] or safeguarded["original_core_modified"]:
        failures.append("Safeguarded iteration archives or scope labels failed validation")
    for name in ["operating_origin_independent_review.json","veu_independent_review.json","safeguarded_independent_review.json"]:
        review=json.loads((ROOT/"outputs/diagnostics"/name).read_text())
        checks+=review["checks"]
        if not review["passed"]:failures.append("Internal independent computational review failed:"+name)
    result=dict(passed=not failures,checked_claims_and_artifacts=checks,failures=failures,freeze="2026-10-11",
                scientific_gaps_are_not_validation_passes=["empirical physical network","population project hazards","causal semiconductor response","historical headline SPOI","continuous MPE"])
    (ROOT/"outputs/diagnostics/data_validation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return int(bool(failures))


if __name__=="__main__":raise SystemExit(main())
