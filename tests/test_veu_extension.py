"""Real-original scope, mutation and source-vintage tests for selected VEU law."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from weaponized.semiconductors.veu_extension import (
    verify_original, permission_rows, removal_rows, issued_veu_events,
)

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def originals():
    book=json.loads((ROOT/'codebooks/veu_extension.json').read_text())
    sources=pd.read_csv(ROOT/'metadata/semiconductor_sources.csv').set_index('source_id')
    result=[]
    for spec in book['documents']:
        result.append((spec,(ROOT/sources.loc[spec['source_id'],'path']).read_bytes(),
                       (ROOT/sources.loc[spec['metadata_source_id'],'path']).read_bytes()))
    return book,result


def test_real_originals_have_every_source_bound_quote_and_two_clocks(originals):
    book,records=originals
    counts=[]
    for spec,body,metadata in records:
        root,claims,clock=verify_original(body,metadata,spec)
        counts.append(len(claims))
        assert clock['info_public_date']<=clock['publication_date']<=clock['effective_date']
    assert counts==[14,4]


def test_named_facility_scopes_and_material_exclusions_are_preserved(originals):
    book,records=originals;spec,body,metadata=records[0]
    root,_,_=verify_original(body,metadata,spec)
    rows=permission_rows(root,spec)
    assert {r['party_id'] for r in rows}=={'samsung_xian','skhynix_wuxi'}
    samsung=next(r for r in rows if r['party_id']=='samsung_xian')
    hynix=next(r for r in rows if r['party_id']=='skhynix_wuxi')
    assert 'NAND memory' in samsung['eligible_items'] and "Xi'an" in samsung['eligible_destination']
    assert '(DRAM)' in hynix['eligible_items'] and 'Wuxi' in hynix['eligible_destination']
    for row in rows:
        assert 'except “extreme ultraviolet”' in row['eligible_items']
        assert '744.6(c)(2)(i-iii)' in row['eligible_items']
        assert '744.23(a)(1)(iii) and (a)(2)(iii)' in row['eligible_items']
        assert '[INSERT PAGE NUMBER]' in row['native_citation']


def test_removal_instruction_explicitly_names_all_three_recipients(originals):
    book,records=originals;spec,body,metadata=records[1]
    root,_,clock=verify_original(body,metadata,spec)
    assert clock['effective_date']=='2025-12-31'
    assert clock['info_public_date']=='2025-08-29'
    rows=removal_rows(root,spec,book['parties'])
    assert {r['party_id'] for r in rows}=={'samsung_xian','skhynix_wuxi','intel_dalian'}
    assert 'eligible_items' not in next(r for r in rows if r['party_id']=='intel_dalian')


@pytest.mark.parametrize('which',['source','metadata'])
def test_original_snapshot_corruption_rejected(originals,which):
    book,records=originals;spec,body,metadata=records[0]
    with pytest.raises(ValueError,match='checksum'):
        verify_original(body+b' ' if which=='source' else body,metadata+b' ' if which=='metadata' else metadata,spec)


@pytest.mark.parametrize('field,value,match',[
    ('document_number','2023-99999','identity'),
    ('publication_date','2023-10-18','date'),
    ('original_citation','invented','citation'),
])
def test_metadata_identity_date_and_citation_not_assumed(originals,field,value,match):
    book,records=originals;spec,body,metadata=records[0]
    modified=deepcopy(spec);modified[field]=value
    with pytest.raises(ValueError,match=match):verify_original(body,metadata,modified)


def test_wrong_exact_quote_rejected(originals):
    book,records=originals;spec,body,metadata=records[0];modified=deepcopy(spec)
    modified['claims'][0]['quote']='This rule is effective October 18, 2023.'
    with pytest.raises(ValueError,match='clause text'):verify_original(body,metadata,modified)


def test_unreviewed_extra_recipient_is_not_silently_accepted(originals):
    book,records=originals;spec,body,metadata=records[0]
    root,_,_=verify_original(body,metadata,spec)
    table=root.find('.//GPOTABLE');new=ET.SubElement(table,'ROW')
    for value in ['New party','All items','New location','New citation']:ET.SubElement(new,'ENT').text=value
    with pytest.raises(ValueError,match='recipient set'):permission_rows(root,spec)


def test_removal_party_crosswalk_requires_literal_source_name(originals):
    book,records=originals;spec,body,metadata=records[1]
    root,_,_=verify_original(body,metadata,spec);parties=deepcopy(book['parties']);parties[0]['removal_party_name']='Invented alias'
    with pytest.raises(ValueError,match='recipient'):removal_rows(root,spec,parties)


def test_announcement_does_not_mean_effective_or_actual_access():
    row=dict(info_public_date='2025-08-29',publication_date='2025-09-02',effective_date='2025-12-31',event_kind='authorization_removal')
    assert issued_veu_events([row],'2025-08-28')==[]
    assert issued_veu_events([row],'2025-08-29')[0]['issued_phase']=='announced_not_effective'
    assert issued_veu_events([row],'2025-08-29','publication')==[]
    late=issued_veu_events([row],'2025-12-31')[0]
    assert late['issued_phase']=='issued_effective_date_reached_not_current_law_certified'
    assert not late['current_authorization_certified'] and late['foreign_access_score'] is None


def test_prior_permissions_remain_historical_versions_after_removal():
    records=[dict(info_public_date='2023-10-13',publication_date='2023-10-17',effective_date='2023-10-17',event_kind='permission_scope_amendment'),
             dict(info_public_date='2025-08-29',publication_date='2025-09-02',effective_date='2025-12-31',event_kind='authorization_removal')]
    result=issued_veu_events(records,'2026-10-11')
    assert len(result)==2 and all(not r['current_authorization_certified'] for r in result)


def test_unknown_clock_is_rejected():
    with pytest.raises(ValueError,match='clock'):issued_veu_events([],'2026-10-11','guessed_first_public')


def test_post_freeze_metadata_publication_cannot_enter_research(originals):
    book,records=originals;spec,body,metadata=records[0]
    changed=deepcopy(spec);record=json.loads(metadata)
    changed['publication_date']=record['publication_date']='2026-10-12'
    payload=json.dumps(record).encode();changed['metadata_sha256']=hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError,match='freeze'):verify_original(body,payload,changed)


def test_explanatory_preamble_is_not_promoted_to_operative_text(originals):
    book,records=originals;spec,body,metadata=records[1];changed=deepcopy(spec)
    next(c for c in changed['claims'] if c['claim_id'].endswith('GENERAL_AUTHORIZATION'))['source_role']='operative_partial_paragraph'
    with pytest.raises(ValueError,match='amended legal text'):verify_original(body,metadata,changed)
