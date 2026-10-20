"""Real-source regression and adversarial checks for printed legal entry units."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from weaponized.semiconductors.entity_schedules import (
    parse_entity_schedule, reported_filing_date, review_category, visible_issued_entries,
    adjudicate_entry_actions,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def original():
    book = json.loads((ROOT/"codebooks/entity_schedules.json").read_text())
    spec = next(x for x in book["documents"] if x["document_number"] == "2025-00480")
    rows = [json.loads(x) for x in (ROOT/"metadata/legal_discovery_acquisitions.jsonl").read_text().splitlines()]
    source = next(x for x in rows if x["source_id"] == spec["source_id"] and x["status"] == "downloaded")
    return (ROOT/source["archive_path"]).read_bytes(), spec


def mutate(original, change):
    root = ET.fromstring(original[0]); change(root)
    payload = ET.tostring(root)
    return payload, original[1] | dict(source_sha256=hashlib.sha256(payload).hexdigest())


def test_complete_source_schedule_and_alias_continuations(original):
    result = parse_entity_schedule(*original)
    assert len(result["entries"]) == 16 and len(result["source_rows"]) == 42
    assert sum(e["destination"] == "SINGAPORE" for e in result["entries"]) == 2
    row = next(e for e in result["entries"] if "Fujian Sophon" in e["entity_first_cell"])
    assert "Fujian Suanfeng" in row["entity_text"] and "Room 916" in row["entity_text"]
    assert len(json.loads(row["source_row_ordinals"])) == 2
    assert row["license_requirement"] == "required_for_printed_scope"
    assert row["foreign_access_score"] is None and row["observed_license_outcome"] is None


def test_original_footnote_is_not_discarded(original):
    result = parse_entity_schedule(*original)
    assert result["entries"][0]["license_footnote_refs"] == '["4"]'
    assert result["entries"][0]["unprinted_footnote_refs"] == '[]'
    assert "foreign-produced items" in result["table_notes"][0]["quote"]
    assert "734.9(e)(2)" in result["table_notes"][0]["quote"]


def test_hash_and_document_identity_are_enforced(original):
    with pytest.raises(ValueError,match="checksum"):
        parse_entity_schedule(original[0]+b" ", original[1])
    with pytest.raises(ValueError,match="identity"):
        parse_entity_schedule(original[0], original[1] | dict(document_number="2025-99999"))


def test_changed_column_order_cannot_silently_change_legal_fields(original):
    payload,spec = mutate(original, lambda root: setattr(root.find('.//BOXHD/CHED[3]'), 'text', 'License review policy'))
    with pytest.raises(ValueError,match="column order"):
        parse_entity_schedule(payload,spec)


def test_missing_destination_is_not_filled_from_entity_address(original):
    def change(root):
        root.find('.//GPOTABLE/ROW[3]/ENT[1]').text = ''
    with pytest.raises(ValueError,match="missing country"):
        parse_entity_schedule(*mutate(original,change))


def test_orphan_continuation_cannot_create_a_new_party(original):
    def change(root):
        row=root.find('.//GPOTABLE/ROW[4]')
        for cell in row.findall('ENT')[2:]:
            cell.clear()
    with pytest.raises(ValueError,match="Orphan"):
        parse_entity_schedule(*mutate(original,change))


def test_detached_review_text_is_not_silently_skipped(original):
    def change(root):
        root.find('.//GPOTABLE/ROW[4]/ENT[3]').clear()
    with pytest.raises(ValueError,match="Detached"):
        parse_entity_schedule(*mutate(original,change))


def test_changed_entry_coverage_requires_re_review(original):
    with pytest.raises(ValueError,match="coverage changed"):
        parse_entity_schedule(original[0],original[1] | dict(expected_printed_entries=15))


@pytest.mark.parametrize(('text','expected'),[
    ('Presumption of denial','presumption_of_denial'),
    ('Policy of denial','policy_of_denial'),
    ('Policy of denial except food/medicine, reviewed on a case-by-case basis','mixed_denial_and_case_by_case'),
    ('Case-by-case basis','case_by_case'),
    ('See § 744.3(d) of the EAR','cross_referenced_review_unresolved'),
])
def test_review_standards_do_not_become_binary_bans(text,expected):
    assert review_category(text)==expected


def test_unknown_review_language_stays_unadjudicated():
    with pytest.raises(ValueError,match="Unreviewed"):
        review_category('automatic approval')


def test_publication_and_reported_filing_clocks_remain_distinct():
    frame=pd.read_csv(ROOT/'data/processed/entity_schedules/entries.csv')
    part=frame[frame.document_number.eq('2025-05427')]
    assert len(visible_issued_entries(part,'2025-03-24'))==0
    assert len(visible_issued_entries(part,'2025-03-25'))==12
    assert len(visible_issued_entries(part,'2025-03-25',clock='publication_date'))==0
    assert len(visible_issued_entries(part,'2025-03-28',clock='publication_date'))==12
    future=frame[frame.document_number.eq('2024-19130')]
    assert len(visible_issued_entries(future,'2024-08-23'))==0  # filed but not yet effective
    with pytest.raises(ValueError,match='freeze'):visible_issued_entries(frame,'2026-10-12')
    with pytest.raises(ValueError,match='Unregistered'):visible_issued_entries(frame,'2026-10-11',clock='retrieval_timestamp')


def test_filing_stamp_is_supported_by_the_named_original():
    assert reported_filing_date('[FR Doc. 2025-05427 Filed 3-25-25; 4:30 pm]','2025-05427')=='2025-03-25'
    with pytest.raises(ValueError,match='dateline'):
        reported_filing_date('[FR Doc. 2025-00480 Filed 3-25-25; 4:30 pm]','2025-05427')


def test_source_placeholders_and_name_spelling_are_preserved():
    frame=pd.read_csv(ROOT/'data/processed/entity_schedules/entries.csv')
    assert frame.entity_text.str.contains('EaseyNovember 1, 2024',regex=False).any()
    assert frame.entity_text.str.startswith('Suma Techology Co., Ltd.').any()
    assert frame.citation_cell_text.str.contains('INSERT FR PAGE NUMBER',regex=False).any()


def test_schedule_versions_are_not_a_count_of_unique_new_firms():
    frame=pd.read_csv(ROOT/'data/processed/entity_schedules/entries.csv')
    assert len(frame)==488 and frame.entry_id.nunique()==488
    assert frame.entry_kind.eq('address_entry').sum()==8
    assert frame.action_adjudication.eq('addition').sum()==395
    assert frame.action_adjudication.eq('revision').sum()==92
    assert frame.action_adjudication.eq('addition_provisional_name_variant').sum()==1
    assert not frame.current_law_consolidation_verified.any()
    assert frame.observed_license_outcome.isna().all()


def test_a_note_not_reprinted_in_this_rule_is_not_borrowed_from_later_law():
    frame=pd.read_csv(ROOT/'data/processed/entity_schedules/entries.csv')
    part=frame[frame.document_number.eq('2024-19130')]
    refs=part[part.license_footnote_refs.eq('["3"]')]
    assert len(refs)>0 and refs.unprinted_footnote_refs.eq('["3"]').all()


def test_mixed_amendments_cannot_be_recoded_as_all_new_additions():
    book=json.loads((ROOT/'codebooks/entity_schedules.json').read_text())
    spec=next(x for x in book['documents'] if x['document_number']=='2024-25411')
    records=map(json.loads,(ROOT/'metadata/legal_discovery_acquisitions.jsonl').read_text().splitlines())
    source=next(x for x in records if x['source_id']==spec['source_id'] and x['status']=='downloaded')
    with pytest.raises(ValueError,match='Uniform-addition'):
        parse_entity_schedule((ROOT/source['archive_path']).read_bytes(),spec|dict(schedule_action='addition'))


@pytest.fixture(scope="module")
def mixed_source():
    book=json.loads((ROOT/'codebooks/entity_schedules.json').read_text())
    spec=next(x for x in book['documents'] if x['document_number']=='2025-17893')
    records=map(json.loads,(ROOT/'metadata/legal_discovery_acquisitions.jsonl').read_text().splitlines())
    source=next(x for x in records if x['source_id']==spec['source_id'] and x['status']=='downloaded')
    crosswalk=pd.read_csv(ROOT/'codebooks/entity_entry_actions.csv',keep_default_na=False)
    return (ROOT/source['archive_path']).read_bytes(),spec,crosswalk[crosswalk.source_id.eq(spec['source_id'])].to_dict('records')


def test_name_spelling_discrepancy_stays_provisional_and_uncorrected(mixed_source):
    payload,spec,crosswalk=mixed_source
    entries=adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],crosswalk)
    row=next(x for x in entries if x['entry_id']=='EL:2025-17893:ROW68')
    assert 'Mircroelectronics' in row['entity_first_cell']
    assert 'Microelectronics' in row['instruction_name']
    assert row['action_adjudication']=='addition_provisional_name_variant'
    assert row['name_variant_requires_expert_review']


def test_revision_cannot_be_changed_to_addition(mixed_source):
    payload,spec,crosswalk=mixed_source
    bad=[dict(x) for x in crosswalk]
    next(x for x in bad if x['action']=='revision')['action']='addition'
    with pytest.raises(ValueError,match='contradicts'):
        adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],bad)


def test_spelling_discrepancy_cannot_be_hidden(mixed_source):
    payload,spec,crosswalk=mixed_source
    bad=[dict(x) for x in crosswalk]
    next(x for x in bad if x['name_variant_requires_expert_review'])['name_variant_requires_expert_review']=False
    with pytest.raises(ValueError,match='discrepancy'):
        adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],bad)


def test_action_crosswalk_cannot_move_a_party_to_another_country(mixed_source):
    payload,spec,crosswalk=mixed_source
    bad=[dict(x) for x in crosswalk];bad[0]['destination']='UNREVIEWED'
    with pytest.raises(ValueError,match='wrong original entry'):
        adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],bad)


def test_a_missing_action_crosswalk_does_not_impute_an_addition(mixed_source):
    payload,spec,crosswalk=mixed_source
    with pytest.raises(ValueError,match='incomplete'):
        adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],crosswalk[:-1])


def test_empty_instruction_name_cannot_match_every_entry(mixed_source):
    payload,spec,crosswalk=mixed_source
    bad=[dict(x) for x in crosswalk];bad[0]['instruction_name']=''
    with pytest.raises(ValueError,match='name or registered operation'):
        adjudicate_entry_actions(payload,spec,parse_entity_schedule(payload,spec)['entries'],bad)
