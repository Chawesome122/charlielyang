"""Extract actual reported MP routing/ownership evidence without inventing flows."""
from pathlib import Path
import json

import pandas as pd

from weaponized.io.schemas import Claim
from weaponized.rare_earths.operating_origin import original_claim, visible_claims, route_evidence_admission

ROOT = Path(__file__).resolve().parents[1]


def build():
    config = json.loads((ROOT/'codebooks/operating_origin_extension.json').read_text())
    sources = json.loads((ROOT/'data/processed/rare_earths/source_index.json').read_text())
    rows = []
    for spec in config['claims']:
        evidence = original_claim(spec, sources, config['source_public_dates'], ROOT)
        source = evidence['source']
        locator = (f"Original HTML; exact normalized quote; ordinal {spec['match_ordinal']}; "
                   f"normalized original chars {evidence['normalized_original_start']}:{evidence['normalized_original_end']}")
        row = {k: spec[k] for k in ['claim_id','entity_id','variable','value','native_unit','product_basis','valid_date','source_id','source_sha256']}
        row.update(observation_id=spec['claim_id'],record_version_id=spec['claim_id']+':'+spec['source_sha256'][:12],
                   info_public_date=source['publication_date'],locator=locator,evidence_class='empirical',event_kind='observed')
        Claim(**{k:row[k] for k in Claim.model_fields if k in row})
        row.update({k:v for k,v in spec.items() if k not in row and k not in {'value_pattern'}})
        row.update(quote=evidence['quote'],source_url=source['url'],source_retrieval_timestamp=source['retrieval_timestamp'],
                   normalized_original_start=evidence['normalized_original_start'],normalized_original_end=evidence['normalized_original_end'],
                   historical_byte_vintage_certified=False,independently_verified_operating_measurement=False,
                   complete_China_free_route_certified=False,empirical_delivered_service=None)
        rows.append(row)
    if len({row['claim_id'] for row in rows}) != len(rows):raise ValueError('Duplicate operating-origin claim identifier')
    out=ROOT/'data/processed/operating_origin_extension';out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'observations.csv',index=False)
    numeric=[r for r in rows if isinstance(r['value'],(float,int))]
    purchases=[r for r in rows if r['variable']=='reported_reagent_and_material_purchases']
    comparisons=[]
    for end,part in pd.DataFrame(purchases).groupby('reporting_period_end',sort=True):
        values=part.value.astype(float)
        comparisons.append(dict(reporting_period_end=end,source_versions=len(part),distinct_source_values=values.nunique(),
                                same_reported_nominal_amount=values.nunique()==1,nominal_USD_million=values.iloc[0],
                                physical_quantity_identified=False,scope_caveat='FY2025 source qualifies purchases to periods when Shenghe was related party; numerical agreement does not identify all inputs or their manufacturing origin'))
    pd.DataFrame(comparisons).to_csv(out/'procurement_comparative_versions.csv',index=False)
    equity=[]
    for year in [2023,2024]:
        part=[r for r in rows if r['source_id']==f'RE-MP-10K{year}' and r['variable']=='reported_equity_interest']
        total=sum(r['value'] for r in part)
        if len(part)!=2 or total!=100:raise ValueError('Reported VREX equity shares do not close')
        equity.append(dict(source_id=f'RE-MP-10K{year}',report_snapshot=f'{year}-12-31',MP_percent=49,Shenghe_percent=51,share_sum_percent=total,passed=True,
                           qualifier='Reported snapshot; no claim of current ownership between unobserved changes'))
    pd.DataFrame(equity).to_csv(out/'reported_equity_closure.csv',index=False)
    origins=['2023-12-31','2024-03-31','2024-12-31','2025-03-31','2025-06-30','2025-12-31','2026-10-11']
    vintages=[]
    for origin in origins:
        visible=visible_claims(rows,origin)
        vintages.append(dict(origin=origin,visible_claims=len(visible),sale_of_49_percent_visible=any(r['claim_id']=='MPOR-2025-VREX-DISPOSAL' for r in visible),
                             July_2025_China_sales_cessation_visible=any(r['claim_id']=='MPOR-2025-CHINA-SALES-CEASE' for r in visible),
                             Q4_2025_internal_feed_visible=any(r['claim_id']=='MPOR-2025-INTERNAL-FEED' for r in visible),
                             current_route_or_ownership_certified=False,information_basis='Selected archived original public clocks; not globally earliest disclosure or first-event surveillance'))
    pd.DataFrame(vintages).to_csv(out/'publication_vintage_checks.csv',index=False)
    cases=[]
    for snapshot in ['2023','2024']:
        for excluded in [False,True]:
            case=route_evidence_admission('Vietnam',True,group_excluded=excluded)
            cases.append(dict(case='VREX_report_snapshot_'+snapshot,processing_country='Vietnam',registered_supplier_group='Shenghe',supplier_group_excluded=excluded,
                              source_id=f'RE-MP-10K{snapshot}',source_public_date=config['source_public_dates'][f'RE-MP-10K{snapshot}'],
                              reported_MP_equity_percent=49,reported_Shenghe_equity_percent=51,**case))
    cases.append(dict(case='Mountain_Pass_to_Independence_Q4_2025',processing_country='United States',registered_supplier_group='unresolved_auxiliary_inputs',supplier_group_excluded=False,
                      source_id='RE-MP-10K2025',source_public_date=config['source_public_dates']['RE-MP-10K2025'],
                      **route_evidence_admission('United States',None)))
    for case in cases:
        case['missing_requirements']=';'.join(case['missing_requirements']);case['failed_requirements']=';'.join(case['failed_requirements'])
    pd.DataFrame(cases).to_csv(out/'route_evidence_admission.csv',index=False)
    result=dict(passed=True,freeze=config['freeze'],source_claims=len(rows),numeric_claims=len(numeric),original_sources=len(config['source_public_dates']),
                equity_closure_checks=len(equity),procurement_comparative_groups=len(comparisons),publication_origins=len(vintages),route_admission_cases=len(cases),
                full_route_data_admitted=sum(x['full_route_data_admitted'] for x in cases),empirical_China_free_service_identified=False,
                event_intervals_are_exact_days=False,current_ownership_carryforward_certified=False,
                causal_policy_effect_identified=False,historical_source_byte_vintage_certified=False,
                source_quote_clock_and_value_checks_passed=True,classification='actual_issuer_disclosures_and_evidence_admission_not_complete_network')
    (ROOT/'outputs/diagnostics/operating_origin_extension_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':build()
