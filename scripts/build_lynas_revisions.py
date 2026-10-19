"""Retain two directly observed comparative-year revisions without overwriting.

The main annual series records each fiscal year's own annual report. This
separate version table makes the observed FY2016 comparisons in FY2017 explicit;
it does not assert complete extraction of every historical restatement.
"""
import json
from pathlib import Path
import re
import pandas as pd
from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text

ROOT=Path(__file__).resolve().parents[1]


def main():
    annual=pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_annual_production.csv")
    sources=pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").set_index("source_id")
    old=annual[annual.period_end.eq("2016-06-30")].copy()
    row=sources.loc["LYNAS-6853554"]
    assert sha256_file(ROOT/row.archive_path)==row.sha256
    text=" ".join(verified_original_text(ROOT/row.archive_path, row.sha256).split())
    patterns={
        "NdPr_oxide_product_family":r"production of NdPr was 5,223 tonnes in FY17 compared to ([\d,]+) tonnes in FY16",
        "total_REO":r"total production of rare earths oxide \(REO\) in FY17 was 16,003 tonnes up from ([\d,]+) tonnes in FY16",
    }
    versions=[]
    for original in old.to_dict("records"):
        product=original['product_basis'];match=re.search(patterns[product],text,re.I)
        if not match:raise ValueError(f"Original comparative evidence not found:{product}")
        base={key:original[key] for key in ['facility_id','period_end','product_basis','native_unit']}
        versions.append(base|dict(value=original['value'],info_public_date=original['info_public_date'],source_id=original['source_id'],source_sha256=original['source_sha256'],version='own_year_original_report',quote_or_locator=original['locator']))
        versions.append(base|dict(value=int(match[1].replace(',','')),info_public_date=row.publication_date,source_id='LYNAS-6853554',source_sha256=row.sha256,version='subsequent_report_comparative',quote_or_locator=match[0]))
    out=ROOT/'data/processed/rare_earths_additional/lynas_observed_revisions.csv'
    pd.DataFrame(versions).to_csv(out,index=False)
    result=dict(records=len(versions),event_period='2016-06-30',original_values_preserved=True,
                cause='not established; no rounding/definition explanation is invented',
                scope='two observed comparisons, not an exhaustive restatement audit')
    (ROOT/'outputs/diagnostics/lynas_revision_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
