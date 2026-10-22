"""Independent read-only stdlib/parser/metadata review of operating-origin claims.

Writes only its own review report. Engineering probes are synthetic inputs, not
measured material routes. This is internal computation, not external certification.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.rare_earths.operating_origin import (
    original_claim, route_evidence_admission, visible_claims,
)

ROOT=Path(__file__).resolve().parents[1]


class IndependentVisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=[]
        self.chunks=[]

    def handle_starttag(self,tag,attrs):
        if tag in {'style','script','ix:header'}:
            self.skip.append(tag)

    def handle_endtag(self,tag):
        if self.skip and self.skip[-1]==tag:
            self.skip.pop()

    def handle_data(self,data):
        if not self.skip:self.chunks.append(data)


def norm(text):
    return ' '.join(text.replace('\u200b','').split())


def main():
    book=json.loads((ROOT/'codebooks/operating_origin_extension.json').read_text())
    index=json.loads((ROOT/'data/processed/rare_earths/source_index.json').read_text())
    checks=[]
    def check(label,passed,**detail):
        checks.append(dict(check=label,passed=bool(passed),**detail))
    source_ids=sorted({r['source_id'] for r in book['claims']})
    texts={}
    source_hashes={}
    for sid in source_ids:
        source=index[sid];payload=(ROOT/source['archive_path']).read_bytes()
        digest=hashlib.sha256(payload).hexdigest();source_hashes[sid]=digest
        check('original_sha256',digest==source['sha256'],source_id=sid)
        parser=IndependentVisibleHTML();parser.feed(payload.decode('utf-8'));parser.close()
        texts[sid]=norm(' '.join(parser.chunks))
    for claim in book['claims']:
        quote=norm(claim['quote']);matches=list(re.finditer(re.escape(quote),texts[claim['source_id']]))
        check('independent_stdlib_original_quote',len(matches)==claim['expected_quote_matches'] and 0<=claim['match_ordinal']<len(matches),claim_id=claim['claim_id'])
    submission=index['RE-MP-SUBMISSIONS'];payload=(ROOT/submission['archive_path']).read_bytes()
    digest=hashlib.sha256(payload).hexdigest();source_hashes['RE-MP-SUBMISSIONS']=digest
    check('independent_submission_metadata_sha256',digest==submission['sha256'])
    recent=json.loads(payload)['filings']['recent']
    for sid in source_ids:
        source=index[sid];name=source['url'].rsplit('/',1)[1];accession=source['url'].split('/')[-2]
        selected=[i for i,item in enumerate(recent['primaryDocument']) if item==name and recent['form'][i]=='10-K' and recent['accessionNumber'][i].replace('-','')==accession]
        check('independent_submission_public_clock',len(selected)==1 and recent['filingDate'][selected[0]]==book['source_public_dates'][sid]==source['publication_date'],source_id=sid,selected_original_public_date=source['publication_date'])
    purchases=[c for c in book['claims'] if c['variable']=='reported_reagent_and_material_purchases']
    for claim in purchases:
        quote=claim['quote'];years=re.findall(r'\b20\d{2}\b',quote);amounts=re.findall(r'\$ ([\d.]+) million',quote)
        pairs=dict(zip(years,map(float,amounts)))
        year=claim['reporting_period_end'][:4]
        check('independent_procurement_year_value_binding',len(years)==len(amounts)==3 and pairs.get(year)==claim['value'],claim_id=claim['claim_id'],reporting_year=year)
        if claim['source_id']=='RE-MP-10K2025':
            check('related_party_period_scope_not_full_year_imputed',claim['financial_period_scope']=='during_period_when_Shenghe_related_party' and 'during the period when Shenghe was considered a related party' in quote,claim_id=claim['claim_id'])
    for claim in book['claims']:
        if claim['variable']=='reported_equity_interest':
            pattern=r'in exchange for a (\d+) % equity interest' if claim['entity_id']=='MP_in_VREX_Holdco' else r'owns the remaining (\d+) % equity interest'
            match=re.search(pattern,claim['quote'])
            check('independent_equity_owner_value_binding',bool(match) and int(match[1])==claim['value'],claim_id=claim['claim_id'])
    by_id={c['claim_id']:c for c in book['claims']}
    expected_intervals={
        'MPOR-2023-VREX-MP-EQUITY':('2023-12-01','2023-12-31','December 2023'),
        'MPOR-2023-TOLLING-UTILIZATION':('2023-10-01','2023-12-31','fourth quarter of 2023'),
        'MPOR-2025-VREX-DISPOSAL':('2025-05-01','2025-05-31','May 2025'),
        'MPOR-2025-CHINA-SALES-CEASE':('2025-07-01','2025-07-31','July 2025'),
        'MPOR-2025-INTERNAL-FEED':('2025-10-01','2025-12-31','fourth quarter of 2025'),
        'MPOR-2025-SHENGHE-STATUS':('2025-10-01','2025-12-31','fourth quarter of 2025')}
    for identifier,(low,high,cue) in expected_intervals.items():
        c=by_id[identifier]
        check('independent_explicit_event_cue_interval',c['event_date_lower']==low and c['event_date_upper']==high and cue in c['quote'] and high<=book['source_public_dates'][c['source_id']],claim_id=identifier)
    commissioning=by_id['MPOR-2025-MAGNET-COMMISSIONING']
    check('year_end_wording_not_forced_into_explicit_quarter',commissioning['event_date_lower'] is None and commissioning['event_date_upper'] is None and 'At the end of 2025' in commissioning['quote'])
    disposal=by_id['MPOR-2025-VREX-DISPOSAL']
    check('independent_divestiture_terms',bool(re.search(r'sold its 49 % interest.*cash payment of \$ 9\.7 million',disposal['quote'])))
    report_rows=pd.read_csv(ROOT/'data/processed/operating_origin_extension/observations.csv',keep_default_na=False)
    check('current_empirical_claims_do_not_certify_independent_operating_truth',report_rows.independently_verified_operating_measurement.astype(str).str.lower().eq('false').all())
    check('outbound_china_sales_not_input_origin_certificate',report_rows.complete_China_free_route_certified.astype(str).str.lower().eq('false').all() and report_rows.empirical_delivered_service.eq('').all())
    admission=pd.read_csv(ROOT/'data/processed/operating_origin_extension/route_evidence_admission.csv',keep_default_na=False)
    check('five_empirical_readiness_cases_remain_unadmitted',len(admission)==5 and admission.full_route_data_admitted.astype(str).str.lower().eq('false').all() and admission.empirical_delivered_service.eq('').all())
    check('seven_missing_requirements_remain_missing',all(len(x.split(';'))==7 for x in admission.missing_requirements) and admission.failed_requirements.eq('').all())
    flags={name:True for name in ['all_input_origins_verified','finite_volume_verified','qualification_verified','ownership_at_origin_verified','material_recipe_and_recovery_verified','route_rights_and_throughput_verified','grade_demand_verified']}
    for country in ['China','china','China ',' china ','CN','PRC','CHN']:
        outcome=route_evidence_admission(country,False,**flags)
        check('synthetic_country_alias_exclusion',not outcome['full_route_data_admitted'],country_input=country)
    try:
        route_evidence_admission('unreviewed nonempty location',False,**flags)
    except ValueError:rejected=True
    else:rejected=False
    check('synthetic_unknown_country_is_not_accepted',rejected)
    for field in flags:
        for value in [None,False]:
            setting=dict(flags);setting[field]=value;outcome=route_evidence_admission('Vietnam',False,**setting)
            classification='missing_requirements' if value is None else 'failed_requirements'
            check('synthetic_missing_false_readiness_guard',not outcome['full_route_data_admitted'] and field in outcome[classification],field=field,input_value=value)
    positive=route_evidence_admission('Vietnam',True,**flags)
    excluded=route_evidence_admission('Vietnam',True,group_excluded=True,**flags)
    check('synthetic_group_sensitivity_is_distinct_from_nationality',positive['full_route_data_admitted'] and not excluded['full_route_data_admitted'] and positive['location_screen']==excluded['location_screen'] and positive['empirical_delivered_service'] is None)
    bad=deepcopy(disposal);bad.update(event_date_lower='2030-05-01',event_date_upper='2030-05-31',valid_date='2030-05-31')
    try:original_claim(bad,index,book['source_public_dates'],ROOT)
    except ValueError:rejected=True
    else:rejected=False
    check('source_inconsistent_future_event_interval_rejected',rejected)
    bad=deepcopy(disposal);bad.update(event_date_lower='2025-06-01',event_date_upper='2025-06-30',valid_date='2025-06-30')
    try:original_claim(bad,index,book['source_public_dates'],ROOT)
    except ValueError:rejected=True
    else:rejected=False
    check('source_inconsistent_but_prepublication_month_rejected',rejected)
    versioned=[dict(c,info_public_date=book['source_public_dates'][c['source_id']]) for c in book['claims']]
    old={r['claim_id'] for r in visible_claims(versioned,'2025-12-31')}
    check('retrospective_event_not_backdated_to_prior_archive',disposal['claim_id'] not in old and all(c['source_id']!='RE-MP-10K2025' for c in versioned if c['claim_id'] in old))
    result=dict(passed=all(c['passed'] for c in checks),review_type='independent_internal_computational_review_not_external_specialist_certification',
                executed_at=datetime.now(timezone.utc).isoformat(),checks=len(checks),failures=[c for c in checks if not c['passed']],details=checks,
                independent_parser='Python standard-library HTMLParser; no original extraction helper used for quote checks',
                original_source_sha256=source_hashes,codebook_sha256=hashlib.sha256((ROOT/'codebooks/operating_origin_extension.json').read_bytes()).hexdigest(),
                reviewed_module_sha256=hashlib.sha256((ROOT/'src/weaponized/rare_earths/operating_origin.py').read_bytes()).hexdigest(),
                original_at_vintage_source_bytes_certified=False,empirical_supply_service_identified=False,
                corporate_national_control_certified=False,initial_failures_preserved='outputs/diagnostics/operating_origin_independent_review_initial_findings.json')
    path=ROOT/'outputs/diagnostics/operating_origin_independent_review.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
    return int(not result['passed'])


if __name__=='__main__':raise SystemExit(main())
