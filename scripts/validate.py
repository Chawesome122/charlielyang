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
        ("white_mesa_validation.json", ["source_claims", "stock_origin_checks", "capacity_component_checks", "product_form_origin_checks", "legacy_basis_corrections"]),
        ("engineering_inputs_validation.json", ["source_claims", "normalized_finite_feed_LP_checks"]),
        ("legal_provisions_validation.json", ["exact_quoted_elements", "exact_dates_elements", "source_artifacts"]),
        ("publication_extension_validation.json", ["source_origin_pairs", "origin_mask_checks", "rejected_auxiliary_date_candidates"]),
    ]:
        report=json.loads((ROOT/"outputs/diagnostics"/diagnostic).read_text())
        checks += sum(report[key] for key in count_fields)
        if not report["passed"]:failures.append(f"Extension validation failed:{diagnostic}")
    result=dict(passed=not failures,checked_claims_and_artifacts=checks,failures=failures,freeze="2026-10-11",
                scientific_gaps_are_not_validation_passes=["empirical physical network","population project hazards","causal semiconductor response","historical headline SPOI","continuous MPE"])
    (ROOT/"outputs/diagnostics/data_validation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return int(bool(failures))


if __name__=="__main__":raise SystemExit(main())
