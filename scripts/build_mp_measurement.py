"""Rebuild MP native volume/monetary-stock tables from original SEC bytes."""
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.original_text import normalize_evidence, verified_original_text
from weaponized.io.schemas import Claim
from weaponized.rare_earths.producer_measurement import asof_native, parse_mp_tables, production_sales_comparison, reconcile_quarters

ROOT = Path(__file__).resolve().parents[1]


def build():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    book = json.loads((ROOT/"codebooks/mp_measurement.json").read_text())
    rows, definitions = [], []
    for sid in book["source_ids"]:
        source = sources[sid]
        if not source.get("publication_date") or source["publication_date"] > book["freeze"]:
            raise ValueError("MP public clock missing or post-freeze")
        year = int(sid[-4:])
        for row in parse_mp_tables((ROOT/source["archive_path"]).read_bytes(), source["sha256"], year):
            oid = f"MP:{row['table_kind']}:{row['variable']}:{row['period_end']}"
            record = row | dict(observation_id=oid, record_version_id=oid+":"+sid, claim_id=oid+":"+sid,
                                entity_id="MP_MountainPass_and_consolidated_inventory", valid_date=row["period_end"],
                                info_public_date=source["publication_date"], source_id=sid, source_sha256=source["sha256"],
                                source_url=source["url"], source_retrieval_timestamp=source["retrieval_timestamp"],
                                evidence_class="empirical", event_kind="observed", historical_byte_vintage_certified=False,
                                actual_physical_stock_identified=False, China_free_service_identified=False,
                                definition_scope="source report definition; comparative-year conversion reconstruction not identified")
            Claim(**{k:record.get(k) for k in Claim.model_fields})
            rows.append(record)
        text = normalize_evidence(verified_original_text(ROOT/source["archive_path"],source["sha256"]))
        for spec in [r for r in book["definitions"] if r["source_id"] == sid]:
            match = re.search(spec["pattern"], text)
            if not match or ("value" in match.groupdict() and float(match["value"]) != spec["value"]):
                raise ValueError("Original named MP definition/value absent")
            row = {k:spec[k] for k in ["claim_id","variable","value","native_unit","interpretation"]}
            row.update(observation_id=f"MP:definition:{spec['variable']}", record_version_id=spec["claim_id"],
                       entity_id="MP_KPI_definitions", product_basis="native_reporting_convention_not_engineering_recipe",
                       valid_date=source["publication_date"], info_public_date=source["publication_date"],
                       valid_date_basis="source-public definition snapshot; convention adoption date unknown except explicitly stated Q4 2025 internal-sales inclusion",
                       source_id=sid,source_sha256=source["sha256"],source_url=source["url"],
                       locator="10-K Key Performance Indicators; exact original regex in codebook", quote=match[0],
                       evidence_class="empirical",event_kind="observed",historical_byte_vintage_certified=False)
            Claim(**{k:row.get(k) for k in Claim.model_fields})
            definitions.append(row)
    frame = pd.DataFrame(rows)
    if frame.record_version_id.duplicated().any():
        raise ValueError("Duplicate MP native cell version")
    out = ROOT/"data/processed/mp_measurement"
    out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"native_cell_versions.csv",index=False)
    pd.DataFrame(definitions).to_csv(out/"definitions.csv",index=False)
    reconciliations = []
    for annual in frame[frame.table_kind.eq("annual")].to_dict("records"):
        q = frame[frame.table_kind.eq("quarterly") & frame.source_id.eq(annual["source_id"]) &
                  frame.variable.eq(annual["variable"]) & frame.period_end.str[:4].eq(annual["period_end"][:4])]
        if q.empty:
            continue
        result = reconcile_quarters(annual,q.to_dict("records"))
        reconciliations.append(dict(source_id=annual["source_id"],year=annual["period_end"][:4],
                                    variable=annual["variable"], **result))
    inventory_checks = []
    for (sid,period), part in frame[frame.table_kind.eq("inventory_currency")].groupby(["source_id","period_end"]):
        values = part.set_index("variable").value.to_dict()
        for identity, lhs, rhs in [
            ("current_components",sum(values[k] for k in ["raw_materials_supplies","mined_ore_stockpiles","work_in_process","finished_goods"]), values["current_total"]),
            ("current_plus_noncurrent",values["current_total"]+values["noncurrent_portion"],values["all_inventory_total"]),
        ]:
            inventory_checks.append(dict(source_id=sid,period_end=period,identity=identity,
                                         component_sum_USD_thousands=lhs,total_USD_thousands=rhs,passed=lhs==rhs,
                                         physical_mass_identified=False))
    agreement = []
    for keys,part in frame.groupby(["table_kind","period_end","variable"]):
        if len(part) < 2:
            continue
        ordered = part.sort_values("info_public_date")
        agreement.append(dict(zip(["table_kind","period_end","variable"],keys)) |
                         dict(source_versions=len(part),earliest_source=ordered.iloc[0].source_id,
                              latest_source=ordered.iloc[-1].source_id,
                              source_tokens_agree=part.source_cell_token.nunique()==1,
                              interpretation="observed comparative values retained; same numbers do not certify unchanged definitions"))
    comparisons = []
    latest = asof_native(frame,book["freeze"])
    for (period,_), part in latest.groupby(["period_end",latest.variable.str.split("_").str[0]]):
        p = part[part.variable.str.endswith("production")]
        s = part[part.variable.str.endswith("sales")]
        if len(p)!=1 or len(s)!=1 or p.iloc[0].cell_status!="reported_number" or s.iloc[0].cell_status!="reported_number":
            continue
        a,b=p.iloc[0].to_dict(),s.iloc[0].to_dict()
        comparisons.append(dict(period_end=period,product_family=a["variable"].split("_")[0],source_id=a["source_id"],
                                info_public_date=a["info_public_date"],production_KPI=a["value"],sales_KPI=b["value"],
                                **production_sales_comparison(a,b)))
    pd.DataFrame(reconciliations).to_csv(out/"quarter_annual_reconciliation.csv",index=False)
    pd.DataFrame(inventory_checks).to_csv(out/"currency_inventory_identities.csv",index=False)
    pd.DataFrame(agreement).to_csv(out/"comparative_vintage_audit.csv",index=False)
    pd.DataFrame(comparisons).to_csv(out/"production_sales_comparisons.csv",index=False)
    latest.to_csv(out/"annual_asof_freeze.csv",index=False)
    result=dict(passed=not any(r["passed"] is False for r in reconciliations+inventory_checks),freeze=book["freeze"],
                original_sources=len(book["source_ids"]),native_cell_versions=len(frame),
                annual_KPI_versions=int(frame.table_kind.eq("annual").sum()),
                quarterly_KPI_versions=int(frame.table_kind.eq("quarterly").sum()),
                currency_inventory_versions=int(frame.table_kind.eq("inventory_currency").sum()),
                definition_claims=len(definitions),not_applicable_cells=int(frame.cell_status.eq("not_applicable").sum()),
                displayed_dash_cells=int(frame.cell_status.eq("displayed_dash").sum()),
                quarter_annual_checks=len(reconciliations),numeric_quarter_annual_identities=sum(r["status"]=="numeric_identity" for r in reconciliations),
                all_not_applicable_comparisons=sum(r["status"]=="all_not_applicable" for r in reconciliations),
                incomplete_numeric_comparisons=sum(r["status"]=="incomplete_numeric_support" for r in reconciliations),
                currency_inventory_identities=len(inventory_checks),comparative_vintage_groups=len(agreement),
                comparative_numeric_changes=sum(not r["source_tokens_agree"] for r in agreement),
                descriptive_production_sales_pairs=len(comparisons),
                actual_physical_inventory_identified=False,chemical_recovery_estimated=False,
                external_NdPr_sales_from_Q4_2025_identified=False,China_free_service_identified=False,
                historical_definition_adoption_dates_identified=False,historical_byte_vintage_certified=False)
    (ROOT/"outputs/diagnostics/mp_measurement_validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise ValueError("MP native accounting reconciliation failed")
    return result


if __name__ == "__main__":
    build()
