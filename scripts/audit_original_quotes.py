"""Recheck legacy quotations and quarterly KPI cells against original bytes."""
import json
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

from weaponized.io.original_text import evidence_pdf_page, verified_original_text, verify_original_quote
from weaponized.rare_earths.reported_output import parse_lynas_quarterly_front_page
from weaponized.rare_earths.producer_measurement import parse_mp_tables
from weaponized.semiconductors.operations import parse_smic_operations
from weaponized.semiconductors.entity_schedules import parse_entity_schedule, reported_filing_date, adjudicate_entry_actions
from weaponized.semiconductors.legal import issued_xml_text
from weaponized.semiconductors.provisions import normalize_text

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in json.loads((ROOT/"metadata/user_supplied_sources.json").read_text()):
        sources[row['source_id']]=row
    for row in pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").fillna("").to_dict("records"):
        sources[row["source_id"]] = row
    smic_book=json.loads((ROOT/"codebooks/smic_operations.json").read_text())
    smic_specs={r["source_id"]:r for r in smic_book["sources"]}
    for row in pd.read_csv(ROOT/"metadata/semiconductor_sources.csv").fillna("").to_dict("records"):
        if row["source_id"] in smic_specs:
            sources[row["source_id"]]=row|dict(archive_path=row["path"])
    tables = [
        "data/processed/rare_earths/observations.csv",
        "data/processed/rare_earths/project_state_evidence.csv",
        "data/processed/rare_earths_additional/lynas_project_history.csv",
        "data/processed/industrial_evidence/project_milestones.csv",
        "data/processed/industrial_evidence/technical_claims.csv",
        "data/processed/project_histories/milestone_versions.csv",
        "data/processed/finance_material/observations.csv",
        "data/processed/engineering_inputs/observations.csv",
        "data/processed/white_mesa/observations.csv",
        "data/processed/operating_origin_extension/observations.csv",
        "data/processed/mp_measurement/definitions.csv",
        "data/processed/smic_operations/source_clocks.csv",
        "data/processed/smic_operations/definitions.csv",
        "data/processed/supplied_evidence/claims.csv",
        "data/processed/supplied_evidence/smic_quarterly_versions.csv",
    ]
    checks = []
    for table in tables:
        for number, row in enumerate(pd.read_csv(ROOT/table).fillna("").to_dict("records")):
            source = sources[row["source_id"]]
            page = evidence_pdf_page(row)
            quote = row["quote"]
            passed = row["source_sha256"] == source["sha256"] and verify_original_quote(
                ROOT/source["archive_path"], source["sha256"], quote, page)
            checks.append(dict(table=table, row_index=number, source_id=row["source_id"],
                               source_sha256=source["sha256"], pdf_page=page,
                               method="normalized verbatim quote in hash-verified supplied copy" if row['source_id'].startswith('UP-') else "normalized verbatim quote in hash-verified original",
                               passed=passed))
    table = "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv"
    parsed = {}
    for number, row in enumerate(pd.read_csv(ROOT/table).to_dict("records")):
        source = sources[row["source_id"]]
        if row["source_id"] not in parsed:
            text = verified_original_text(ROOT/source["archive_path"], source["sha256"])
            parsed[row["source_id"]] = parse_lynas_quarterly_front_page(text.split("\f")[0])
        keys = ["period_end", "fiscal_quarter", "product_basis", "value", "source_unit_token", "comparative", "report_period_end"]
        matches = [item for item in parsed[row["source_id"]] if all(item[key] == row[key] for key in keys)]
        checks.append(dict(table=table, row_index=number, source_id=row["source_id"],
                           source_sha256=source["sha256"], pdf_page=1,
                           method="reparse original three-column quarterly KPI header and cells",
                           passed=len(matches) == 1 and row["source_sha256"] == source["sha256"]))
    table = "data/processed/mp_measurement/native_cell_versions.csv"
    parsed = {}
    for number, row in enumerate(pd.read_csv(ROOT/table,keep_default_na=False).to_dict("records")):
        sid=row["source_id"];source=sources[sid]
        if sid not in parsed:
            parsed[sid]={(r["table_kind"],r["variable"],r["period_end"]):r for r in
                         parse_mp_tables((ROOT/source["archive_path"]).read_bytes(),source["sha256"],int(sid[-4:]))}
        expected=parsed[sid].get((row["table_kind"],row["variable"],row["period_end"]))
        fields=["source_cell_token","cell_status","product_basis","native_unit","quote","table_ordinal","row_ordinal"]
        passed=(expected is not None and all(row[k]==expected[k] for k in fields) and
                ((expected["value"] is None and row["value"]=="") or
                 (expected["value"] is not None and float(row["value"])==expected["value"])) and
                row["source_sha256"]==source["sha256"] and row["info_public_date"]==source["publication_date"])
        checks.append(dict(table=table,row_index=number,source_id=sid,source_sha256=source["sha256"],pdf_page=None,
                           method="reparse original named row, annual/quarterly header, cell token, unit and missing-state",passed=passed))
    table="data/processed/smic_operations/observations.csv"
    parsed={}
    for number,row in enumerate(pd.read_csv(ROOT/table).to_dict("records")):
        sid=row["source_id"];source=sources[sid]
        if sid not in parsed:
            text=verified_original_text(ROOT/source["archive_path"],source["sha256"])
            parsed[sid]={(r["variable"],r["period_end"],r["period_frequency"]):r for r in parse_smic_operations(text,smic_specs[sid])}
        expected=parsed[sid].get((row["variable"],row["period_end"],row["period_frequency"]))
        fields=["value","source_cell_token","native_unit","product_basis","source_definition_version","measurement_timing","pdf_page","quote","header_quote","locator"]
        checks.append(dict(table=table,row_index=number,source_id=sid,source_sha256=source["sha256"],pdf_page=row["pdf_page"],
                           method="reparse exact original PDF page, named row/phrase, period header, unit and source dateline",
                           passed=expected is not None and all(row[k]==expected[k] for k in fields) and row["source_sha256"]==source["sha256"] and row["info_public_date"]==smic_specs[sid]["info_public_date"]))
    # XML schedules require explicit original XML locators and structural entry
    # re-extraction. Do not treat a derived flattened XML/text aid as evidence.
    entity_book=json.loads((ROOT/"codebooks/entity_schedules.json").read_text())
    legal_sources={r["source_id"]:r for r in map(json.loads,(ROOT/"metadata/legal_discovery_acquisitions.jsonl").read_text().splitlines()) if r["status"]=="downloaded"}
    entity_originals={}
    action_crosswalk=pd.read_csv(ROOT/"codebooks/entity_entry_actions.csv",keep_default_na=False)
    for spec in entity_book["documents"]:
        source=legal_sources[spec["source_id"]]
        payload=(ROOT/source["archive_path"]).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=spec["source_sha256"] or source["sha256"]!=spec["source_sha256"]:
            raise ValueError("Original Entity List snapshot hash mismatch")
        issued_xml_text(payload,spec["document_number"])
        root=ET.fromstring(payload)
        raw_entries=parse_entity_schedule(payload,spec)["entries"]
        crosswalk=action_crosswalk[action_crosswalk.source_id.eq(spec["source_id"])].to_dict("records")
        parsed_entries={x["entry_id"]:x for x in adjudicate_entry_actions(payload,spec,raw_entries,crosswalk)}
        entity_originals[spec["source_id"]]=(source,root,parsed_entries,spec)
    for name in ["source_rows","table_notes","amendatory_instructions","source_clocks"]:
        table=f"data/processed/entity_schedules/{name}.csv"
        for number,row in enumerate(pd.read_csv(ROOT/table,keep_default_na=False).to_dict("records")):
            source,root,_,spec=entity_originals[row["source_id"]]
            fields=[("xpath","quote")]+([("filing_xpath","filing_quote")] if name=="source_clocks" else [])
            for xpath_field,quote_field in fields:
                nodes=root.findall(row[xpath_field])
                checks.append(dict(table=table,row_index=number,source_id=row["source_id"],source_sha256=source["sha256"],pdf_page=None,
                                   method="exact original issued-XML XPath and text; filing/effective dates separate",
                                   passed=len(nodes)==1 and normalize_text(nodes[0])==row[quote_field] and row["source_sha256"]==source["sha256"]))
    table="data/processed/entity_schedules/entries.csv"
    for number,row in enumerate(pd.read_csv(ROOT/table,keep_default_na=False).to_dict("records")):
        source,root,parsed,spec=entity_originals[row["source_id"]]
        expected=parsed.get(row["entry_id"])
        fields=["destination","country_xpath","start_row_ordinal","start_xpath","entity_first_cell","entity_text",
                "source_row_ordinals","license_scope_text","review_policy_text","citation_cell_text","review_category",
                "entry_kind","license_requirement","license_footnote_refs","unprinted_footnote_refs","action_adjudication",
                "action_evidence_method","action_source_xpath","instruction_name","name_variant_requires_expert_review"]
        blank_scores=all(row[k]=="" for k in ["observed_license_outcome","foreign_access_score","domestic_capability_score","causal_effect"])
        passed=expected is not None and all(row[k]==expected[k] for k in fields) and blank_scores and not row["current_law_consolidation_verified"]
        passed &= row["source_sha256"]==source["sha256"] and row["info_public_date"]==reported_filing_date(normalize_text(root.find("./FRDOC")),spec["document_number"])
        passed &= row["publication_date"]==spec["publication_date"] and row["effective_date"]==spec["effective_date"]
        checks.append(dict(table=table,row_index=number,source_id=row["source_id"],source_sha256=source["sha256"],pdf_page=None,
                           method="reparse original five-column entry, aliases/continuations, destination, notes, review and dateline; unknown outcomes stay blank",passed=passed))
    veu_sources=pd.read_csv(ROOT/"metadata/semiconductor_sources.csv",keep_default_na=False).set_index("source_id")
    veu_originals={}
    for spec in json.loads((ROOT/"codebooks/veu_extension.json").read_text())["documents"]:
        source=veu_sources.loc[spec["source_id"]]
        payload=(ROOT/source.path).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=spec["source_sha256"] or source.sha256!=spec["source_sha256"]:
            raise ValueError("VEU original snapshot mismatch")
        issued_xml_text(payload,spec["document_number"])
        veu_originals[spec["source_id"]]=(source,ET.fromstring(payload))
    table="data/processed/veu_extension/clauses.csv"
    for number,row in enumerate(pd.read_csv(ROOT/table,keep_default_na=False).to_dict("records")):
        source,root=veu_originals[row["source_id"]]
        nodes=root.findall(row["xpath"])
        checks.append(dict(table=table,row_index=number,source_id=row["source_id"],source_sha256=source.sha256,pdf_page=None,
                           method="exact original VEU issued-XML XPath and text, without treating explanatory material as operative law",
                           passed=len(nodes)==1 and normalize_text(nodes[0])==row["quote"] and row["source_sha256"]==source.sha256))
    out = ROOT/"data/processed/source_integrity"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(out/"original_quote_audit.csv", index=False)
    result = dict(passed=all(row["passed"] for row in checks), checks=len(checks),
                  tables=len(tables)+3+5+1, original_sources=len({row["source_id"] for row in checks}),
                  failures=[row for row in checks if not row["passed"]],
                  editable_text_aids_used=False, independent_production_measurement=False,
                  historical_source_byte_vintage_certified=False,
                  scope="Present archived source-byte support, including supplied browser-print copies; not historical release certification or independent economic truth")
    (ROOT/"outputs/diagnostics/original_quote_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
