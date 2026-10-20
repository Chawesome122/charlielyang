"""Extract source-vintaged semiconductor operating scale/inputs, without z/f scores."""
from datetime import datetime
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.original_text import normalize_evidence, verified_original_text
from weaponized.io.schemas import Claim
from weaponized.semiconductors.operations import asof_operations, parse_smic_operations, smic_definition_quotes

ROOT=Path(__file__).resolve().parents[1]


def build():
    book=json.loads((ROOT/"codebooks/smic_operations.json").read_text())
    sources=pd.read_csv(ROOT/"metadata/semiconductor_sources.csv").fillna("").set_index("source_id")
    rows,clocks,definitions=[],[],[]
    for spec in book["sources"]:
        source=sources.loc[spec["source_id"]]
        original=verified_original_text(ROOT/source.path,source.sha256)
        first=normalize_evidence(original.split("\f")[0])
        display=datetime.strptime(spec["info_public_date"],"%Y-%m-%d").strftime("%B %-d, %Y")
        match=re.search("Shanghai, China – "+re.escape(display)+" – Semiconductor Manufacturing International Corporation",first)
        if not match:raise ValueError("Exact issuer dateline absent from first PDF page")
        clocks.append(dict(source_id=spec["source_id"],source_sha256=source.sha256,source_url=source.url,
                           info_public_date=spec["info_public_date"],pdf_page=1,quote=match[0],
                           locator="PDF page 1; issuer release dateline, not conference-call or reporting-period date",
                           method="issuer_stated_release_date_in_original_first_page",historical_byte_vintage_certified=False))
        for definition in smic_definition_quotes(original,spec):
            definitions.append(definition|dict(claim_id=spec["source_id"]+":"+definition["definition"],source_id=spec["source_id"],source_sha256=source.sha256,
                                               info_public_date=spec["info_public_date"],source_url=source.url,
                                               locator=f"PDF page {definition['pdf_page']}; original operating unit/denominator definition",
                                               historical_definition_adoption_date_known=False))
        for item in parse_smic_operations(original,spec):
            oid=f"SMIC:{item['variable']}:{item['period_frequency']}:{item['period_end']}"
            row=item|dict(observation_id=oid,record_version_id=oid+":"+spec["source_id"],claim_id=oid+":"+spec["source_id"],
                          entity_id="SMIC_consolidated_reported_operations",valid_date=item["period_end"],
                          valid_date_basis="reporting-period endpoint; detailed monthly-rate measurement day unknown; rounded annual capacity summary explicitly year end",
                          info_public_date=spec["info_public_date"],source_id=spec["source_id"],source_sha256=source.sha256,
                          source_url=source.url,source_retrieval_timestamp=source.retrieval_timestamp,
                          evidence_class="empirical",event_kind="observed",reporting_status="issuer_reported_in_unaudited_earnings_release",
                          target_specific_capability_identified=False,foreign_access_identified=False,
                          combined_availability_identified=False,causal_effect_identified=False,
                          historical_byte_vintage_certified=False,
                          definition_scope="current source wording, including comparatives; historical conversion/adoption not independently reconstructed")
            Claim(**{key:row.get(key) for key in Claim.model_fields})
            rows.append(row)
    frame=pd.DataFrame(rows)
    if frame.record_version_id.duplicated().any():raise ValueError("Duplicate SMIC version")
    out=ROOT/"data/processed/smic_operations";out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"observations.csv",index=False)
    pd.DataFrame(clocks).to_csv(out/"source_clocks.csv",index=False)
    pd.DataFrame(definitions).to_csv(out/"definitions.csv",index=False)
    latest=asof_operations(frame,book["freeze"])
    latest.to_csv(out/"observations_asof_freeze.csv",index=False)
    share_checks=[]
    for (sid,period),part in frame[frame.period_frequency.eq("quarter")].groupby(["source_id","period_end"]):
        v=part.set_index("variable").value
        for name,keys in [("service_revenue",["wafer_service_revenue_share","other_service_revenue_share"]),
                          ("wafer_size_revenue",["wafer_8inch_revenue_share","wafer_12inch_revenue_share"])]:
            total=float(v[keys].sum())
            share_checks.append(dict(source_id=sid,period_end=period,identity=name,sum_percent=total,
                                     passed=abs(total-100)<1e-10,physical_output_share_identified=False))
    pd.DataFrame(share_checks).to_csv(out/"revenue_share_identities.csv",index=False)
    precision=[]
    for sid,part in frame.groupby("source_id"):
        year=int(sid[10:14]);period=f"{year}-12-31"
        a=part[part.variable.eq("rounded_yearend_monthly_capacity")].iloc[0]
        b=part[part.variable.eq("monthly_capacity") & part.period_end.eq(period)].iloc[0]
        difference=float(a.value*1000-b.value)
        precision.append(dict(source_id=sid,period_end=period,summary_native_thousands=float(a.value),detailed_native_units=float(b.value),
                              difference_native_units=difference,display_rounding_consistent=abs(difference)<=500,
                              physical_capacity_uncertainty_interval=None,
                              interpretation="thousand-unit presentation comparison only; not a utilization/production identity or confidence interval"))
    pd.DataFrame(precision).to_csv(out/"capacity_presentation_audit.csv",index=False)
    vintages=[]
    for (variable,period,frequency),part in frame.groupby(["variable","period_end","period_frequency"]):
        if len(part)<2:continue
        part=part.sort_values("info_public_date")
        vintages.append(dict(variable=variable,period_end=period,period_frequency=frequency,source_versions=len(part),
                             earlier_source=part.iloc[0].source_id,later_source=part.iloc[-1].source_id,
                             earlier_value=float(part.iloc[0].value),later_value=float(part.iloc[-1].value),
                             observed_values_agree=part.value.nunique()==1,basis_wording_agrees=part.product_basis.nunique()==1,
                             definition_wording_agrees=part.source_definition_version.nunique()==1,
                             historical_conversion_identified=False))
    pd.DataFrame(vintages).to_csv(out/"comparative_vintages.csv",index=False)
    finance=pd.read_csv(ROOT/"data/processed/semiconductors/reported_financial_inputs.csv")
    rd=frame[frame.variable.eq("rd_expense") & frame.period_end.str.endswith("12-31")]
    matches=0
    for r in rd.to_dict("records"):
        if r["period_end"][:4]!=r["source_id"][10:14]:
            continue  # Prior-year comparative is not this source's own-year input.
        old=finance[finance.source_id.eq(r["source_id"]) & finance.variable.eq("fourth_quarter_rd_expense")]
        if len(old)!=1 or float(old.iloc[0].value_USD)!=r["value"]*1000:raise ValueError("Existing Q4 R&D input disagrees with named source row")
        matches+=1
    result=dict(passed=all(r["passed"] for r in share_checks) and all(r["display_rounding_consistent"] for r in precision),
                freeze=book["freeze"],source_claims=len(frame),original_sources=len(clocks),verified_source_clocks=len(clocks),
                definition_claims=len(definitions),
                latest_cells=len(latest),distinct_quarterly_periods=int(latest[latest.period_frequency.eq("quarter")].period_end.nunique()),
                revenue_share_identities=len(share_checks),capacity_presentation_checks=len(precision),
                comparative_vintage_groups=len(vintages),comparative_value_changes=sum(not r["observed_values_agree"] for r in vintages),
                comparative_basis_wording_changes=sum(not r["basis_wording_agrees"] for r in vintages),existing_R_and_D_crosschecks=matches,
                comparative_definition_wording_changes=sum(not r["definition_wording_agrees"] for r in vintages),
                target_capability_scores_assigned=0,foreign_access_scores_assigned=0,game_x_identified=False,
                aggregate_output_is_indigenous_target_capability=False,continuous_quarterly_panel=False,
                causal_effect_estimated=False,source_byte_historical_vintage_certified=False)
    (ROOT/"outputs/diagnostics/smic_operations_validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:raise ValueError("SMIC operating measurement validation failed")
    return result


if __name__ == "__main__":build()
