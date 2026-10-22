"""Scientific failure cases for late-supplied copies and native measurement."""
import copy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.io.supplied_evidence import asof_supplied, extract_claim, source_pages, stated_event_window
from weaponized.semiconductors.supplied_operations import parse_quarterly_release
from weaponized.rare_earths.supplied_projects import supplied_project_snapshots

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def evidence():
    sources=json.loads((ROOT/'metadata/user_supplied_sources.json').read_text())
    book=json.loads((ROOT/'codebooks/supplied_evidence.json').read_text())
    return book,{s['source_id']:s for s in sources},{s['source_id']:source_pages(ROOT,s) for s in sources}


@pytest.mark.parametrize('phrase,lower,upper',[
    ('March 2026','2026-03-01','2026-03-31'),('February 2024','2024-02-01','2024-02-29'),
    ('first quarter of 2026','2026-01-01','2026-03-31'),('the third quarter of 2026','2026-07-01','2026-09-30'),
    ('August 7, 2026','2026-08-07','2026-08-07'),('2028','2028-01-01','2028-12-31')])
def test_source_date_precision(phrase,lower,upper):
    assert stated_event_window(phrase)==(lower,upper)


def test_copy_creation_is_not_historical_clock(evidence):
    _,sources,_=evidence
    mp=next(s for s in sources.values() if s['request_rank']==1)
    assert 'Oct 22' in mp['pdfinfo'] and mp['info_public_date']=='2026-08-07'
    assert mp['representation']=='browser_print_of_sec_html'
    assert not mp['historical_byte_vintage_certified'] and not mp['transport_verified']


@pytest.mark.parametrize('field,value',[('sha256','0'*64),('bytes',0),('pdf_pages',1)])
def test_archive_mutation_rejected(evidence,field,value):
    _,sources,_=evidence
    s=copy.deepcopy(next(iter(sources.values())));s[field]=value
    with pytest.raises(ValueError):source_pages(ROOT,s)


@pytest.mark.parametrize('page',[0,True,9999])
def test_claim_needs_real_pdf_page(evidence,page):
    book,sources,pages=evidence;c=copy.deepcopy(book['claims'][0]);c['pdf_page']=page
    with pytest.raises(ValueError):extract_claim(pages[c['source_id']],c,sources[c['source_id']])


def test_nearby_numeric_token_does_not_support_wrong_cell(evidence):
    book,sources,pages=evidence;c=copy.deepcopy(book['claims'][0])
    # 597 appears on the same row, but is the previous-year cell.
    c['value']=597
    with pytest.raises(ValueError,match='named source cell'):extract_claim(pages[c['source_id']],c,sources[c['source_id']])


def test_wrong_period_header_rejected(evidence):
    book,sources,pages=evidence;c=copy.deepcopy(book['claims'][0]);c['header_pattern']='2026 2025 Unit % 2025 2026 Unit %'
    with pytest.raises(ValueError):extract_claim(pages[c['source_id']],c,sources[c['source_id']])


@pytest.mark.parametrize('change',[{'event_start':'2026-02-01'},{'event_end':'2026-04-30'},{'event_date_phrase':'March 2025'}])
def test_upton_date_interval_cannot_drift(evidence,change):
    book,sources,pages=evidence;c=copy.deepcopy(next(x for x in book['claims'] if x['variable']=='rer_demo_start'));c.update(change)
    with pytest.raises(ValueError):extract_claim(pages[c['source_id']],c,sources[c['source_id']])


def test_target_retained_as_plan_not_observed_survival(evidence):
    book,sources,pages=evidence;c=next(x for x in book['claims'] if x['variable']=='usar_blacksburg_plan')
    r=extract_claim(pages[c['source_id']],c,sources[c['source_id']])
    assert r['event_kind']=='planned' and r['event_end']=='2028-12-31'
    wrong=c|dict(event_kind='observed')
    with pytest.raises(ValueError,match='after its source'):extract_claim(pages[c['source_id']],wrong,sources[c['source_id']])


def test_no_prepublication_leak_from_retroactive_event(evidence):
    book,sources,pages=evidence;c=next(x for x in book['claims'] if x['variable']=='mp_ratio_adoption')
    r=extract_claim(pages[c['source_id']],c,sources[c['source_id']]);frame=pd.DataFrame([r])
    assert asof_supplied(frame,'2026-03-31').empty
    assert len(asof_supplied(frame,'2026-08-07'))==1
    with pytest.raises(ValueError):asof_supplied(frame,'2026-10-12')


def test_postfreeze_document_rejected(evidence):
    book,sources,pages=evidence;c=book['claims'][0];s=sources[c['source_id']]|dict(info_public_date='2026-10-12')
    with pytest.raises(ValueError,match='Post-freeze'):extract_claim(pages[c['source_id']],c,s)


def test_smic_q1_rolls_previous_quarter_to_prior_year(evidence):
    book,sources,pages=evidence;spec=book['smic_sources'][0];s=sources[spec['source_id']]
    rows=parse_quarterly_release(pages[s['source_id']],spec,s)
    cells={(r['variable'],r['period_end']):r['value'] for r in rows}
    assert cells['wafer_shipments','2026-03-31']==2509137
    assert cells['wafer_shipments','2025-12-31']==2514970
    assert cells['wafer_shipments','2025-03-31']==2292153
    assert cells['monthly_capacity','2026-03-31']==1078250
    assert all(not r['target_capability_identified'] for r in rows)


@pytest.mark.parametrize('wrong', ['header','definition','dateline','report_period'])
def test_smic_rejects_unbound_native_semantics(evidence,wrong):
    book,sources,pages=evidence;spec=book['smic_sources'][0];s=sources[spec['source_id']];p=pages[s['source_id']].copy()
    if wrong=='header':p[4]=p[4].replace('1Q26 4Q25 QoQ 1Q25 YoY','1Q26 1Q25 QoQ 4Q25 YoY')
    elif wrong=='definition':p[4]=p[4].replace('Based on standard logic 8-inch equivalent wafers.','Based on unspecified units.')
    elif wrong=='dateline':p[0]=p[0].replace('May 14, 2026','May 15, 2026')
    else:spec=spec|dict(quarter=2)
    with pytest.raises(ValueError):parse_quarterly_release(p,spec,s)


@pytest.mark.parametrize('section', ['service','size','R_and_D'])
def test_correct_neighbor_header_cannot_validate_wrong_subtable(evidence,section):
    book,sources,pages=evidence;spec=book['smic_sources'][0];s=sources[spec['source_id']];p=pages[s['source_id']].copy()
    if section=='service':p[4]=p[4].replace('By Service Type 1Q26 4Q25 1Q25','By Service Type 1Q26 1Q25 4Q25')
    elif section=='size':p[4]=p[4].replace('1Q26 4Q25 1Q25 By Size','1Q26 1Q25 4Q25 By Size')
    else:
        head,tail=p[5].split('Operating Expenses',1)
        p[5]=head+'Operating Expenses'+tail.replace('1Q26 4Q25 QoQ 1Q25 YoY','1Q26 1Q25 QoQ 4Q25 YoY',1)
    with pytest.raises(ValueError):parse_quarterly_release(p,spec,s)


def test_white_mesa_conflicting_versions_stay_separate(evidence):
    book,sources,pages=evidence
    selected=[extract_claim(pages[c['source_id']],c,sources[c['source_id']]) for c in book['claims'] if c['variable'] in ['wm_heavies_prose_tb','wm_table_tb_phase1']]
    assert {r['value'] for r in selected}=={14,20}
    assert all(r['event_kind']=='planned' and not r['empirical_service_identified'] for r in selected)


def test_missing_document_not_marked_received(evidence):
    _,sources,_=evidence
    assert len(sources)==10 and 7 not in {s['request_rank'] for s in sources.values()}


def test_discovery_extension_does_not_promote_targets_or_demos(evidence):
    book,sources,pages=evidence
    claims=pd.DataFrame([extract_claim(pages[c['source_id']],c,sources[c['source_id']]) for c in book['claims']])
    roster=supplied_project_snapshots(claims).set_index('activity_id')
    assert len(roster)==8 and roster.project_id.nunique()==6
    assert roster.loc['RER_Upton_separation','state']=='Q'
    assert roster.loc['USARE_WheatRidge_separation','state']=='Q'
    assert roster.loc['RER_Upton_separation','event_date_lower']=='2026-03-01'
    for a in ['USARE_Blacksburg_magnet','USARE_Blacksburg_alloy']:
        assert roster.loc[a,'state']=='F' and pd.isna(roster.loc[a,'event_date_upper'])
    assert roster.loc['MP_10X_magnet','state']=='C' and pd.isna(roster.loc['MP_10X_magnet','event_date_lower'])
    assert roster.capacity_native.isna().all() and not roster.commercial_network_ready.any()
