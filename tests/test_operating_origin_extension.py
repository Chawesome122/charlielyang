"""Original-byte, value, vintage and route-admission safeguards."""
from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.rare_earths.operating_origin import original_claim, route_evidence_admission, visible_claims

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'codebooks/operating_origin_extension.json').read_text())
SOURCES = json.loads((ROOT/'data/processed/rare_earths/source_index.json').read_text())


def spec(identifier):
    return deepcopy(next(x for x in CONFIG['claims'] if x['claim_id']==identifier))


def test_all_registered_source_quotes_and_numeric_values_reextract_from_originals():
    assert len(CONFIG['claims'])==33
    for claim in CONFIG['claims']:
        result=original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)
        assert result['quote']==claim['quote']
        assert result['normalized_original_end']>result['normalized_original_start']
    disposal=spec('MPOR-2025-VREX-DISPOSAL')
    assert disposal['event_date_lower']=='2025-05-01' and disposal['event_date_upper']=='2025-05-31'
    assert disposal['value']==49


def test_changed_original_snapshot_is_rejected_even_with_an_existing_text_cache(tmp_path):
    claim=spec('MPOR-2023-VREX-MP-EQUITY');sources=deepcopy(SOURCES)
    path=tmp_path/'source.html';path.write_bytes((ROOT/sources[claim['source_id']]['archive_path']).read_bytes())
    sources[claim['source_id']]['archive_path']=str(path)
    original_claim(claim,sources,CONFIG['source_public_dates'],ROOT)
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='checksum'):
        original_claim(claim,sources,CONFIG['source_public_dates'],ROOT)


def test_ownership_value_cannot_be_swapped_for_the_other_partner_share():
    claim=spec('MPOR-2023-VREX-MP-EQUITY');claim['value']=51
    with pytest.raises(ValueError,match='named source binding'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


def test_removing_quote_or_changing_its_source_is_rejected():
    claim=spec('MPOR-2025-VREX-DISPOSAL');claim['quote']=''
    with pytest.raises(ValueError,match='Empty evidence'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)
    claim=spec('MPOR-2025-VREX-DISPOSAL');claim['source_id']='RE-MP-10K2024'
    with pytest.raises(ValueError,match='digest differs'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


@pytest.mark.parametrize('bad_date',[None,'2025-12-31','2026-10-12'])
def test_changed_missing_or_postfreeze_source_clock_is_rejected(bad_date):
    claim=spec('MPOR-2025-VREX-DISPOSAL');sources=deepcopy(SOURCES)
    sources[claim['source_id']]['publication_date']=bad_date
    with pytest.raises(ValueError,match='clock'):
        original_claim(claim,sources,CONFIG['source_public_dates'],ROOT)


def test_event_interval_cannot_be_reversed_or_presented_as_an_exact_index_day():
    claim=spec('MPOR-2025-VREX-DISPOSAL');claim['event_date_lower']='2025-06-01'
    with pytest.raises(ValueError,match='interval'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)
    claim=spec('MPOR-2025-VREX-DISPOSAL');claim['valid_date']='2025-05-01'
    with pytest.raises(ValueError,match='indexing date'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


def test_reported_disposal_is_not_backdated_into_prior_archive_information_sets():
    claims=[dict(c,info_public_date=CONFIG['source_public_dates'][c['source_id']]) for c in CONFIG['claims']]
    old=visible_claims(claims,'2025-12-31');new=visible_claims(claims,'2026-02-26')
    assert 'MPOR-2025-VREX-DISPOSAL' not in {c['claim_id'] for c in old}
    assert 'MPOR-2025-VREX-DISPOSAL' in {c['claim_id'] for c in new}
    assert all(c['info_public_date']<='2025-12-31' for c in old)
    assert not visible_claims(claims,'2023-12-31')


def test_nonchina_processing_location_does_not_create_missing_origin_or_service_evidence():
    result=route_evidence_admission('Vietnam',True)
    assert result['location_screen']=='not_excluded_by_reported_location_alone'
    assert not result['full_route_data_admitted']
    assert len(result['missing_requirements'])==7 and result['empirical_delivered_service'] is None


def test_registered_supplier_group_removal_is_distinct_from_processing_geography():
    requirements=dict(all_input_origins_verified=True,finite_volume_verified=True,qualification_verified=True,ownership_at_origin_verified=True,material_recipe_and_recovery_verified=True,route_rights_and_throughput_verified=True,grade_demand_verified=True)
    base=route_evidence_admission('Vietnam',True,**requirements)
    removed=route_evidence_admission('Vietnam',True,group_excluded=True,**requirements)
    assert base['full_route_data_admitted'] and not removed['full_route_data_admitted']
    assert base['location_screen']==removed['location_screen']
    assert removed['supplier_group_screen']=='excluded_by_registered_supplier_group_sensitivity'
    assert removed['empirical_delivered_service'] is None


def test_reported_china_location_fails_location_screen_even_when_other_fields_are_present():
    result=route_evidence_admission('China',False,all_input_origins_verified=True,finite_volume_verified=True,qualification_verified=True,ownership_at_origin_verified=True,material_recipe_and_recovery_verified=True,route_rights_and_throughput_verified=True,grade_demand_verified=True)
    assert not result['full_route_data_admitted']
    assert result['location_screen']=='excluded_by_reported_processing_location'


def test_unknown_origin_and_failed_origin_are_distinct_and_integer_boolean_is_rejected():
    missing=route_evidence_admission(None,None)
    failed=route_evidence_admission('United States',None,all_input_origins_verified=False)
    assert 'all_input_origins_verified' in missing['missing_requirements']
    assert 'all_input_origins_verified' in failed['failed_requirements']
    with pytest.raises(ValueError,match='must be'):
        route_evidence_admission('Vietnam',True,finite_volume_verified=1)


def test_2025_procurement_source_scope_and_units_are_preserved_without_annualization():
    rows=[c for c in CONFIG['claims'] if c['variable']=='reported_reagent_and_material_purchases']
    assert len(rows)==9
    latest=spec('MPOR-2025-REAGENT-PURCHASES-2025')
    assert latest['value']==19.7 and latest['native_unit']=='USD million'
    assert latest['financial_period_scope']=='during_period_when_Shenghe_related_party'
    assert 'during the period when Shenghe was considered a related party' in latest['quote']


@pytest.mark.parametrize('country',['china','China ',' china ','CN','CHN','PRC',"China (People's Republic of)"])
def test_reviewed_china_aliases_cannot_escape_the_location_exclusion(country):
    result=route_evidence_admission(country,False,all_input_origins_verified=True,finite_volume_verified=True,qualification_verified=True,ownership_at_origin_verified=True,material_recipe_and_recovery_verified=True,route_rights_and_throughput_verified=True,grade_demand_verified=True)
    assert not result['full_route_data_admitted'] and result['location_screen']=='excluded_by_reported_processing_location'


@pytest.mark.parametrize('country',['Invented free supply jurisdiction','France',123])
def test_unreviewed_country_representations_are_not_assumed_to_be_nonchina(country):
    with pytest.raises(ValueError,match='country'):
        route_evidence_admission(country,False)


@pytest.mark.parametrize('lower,upper',[('2030-05-01','2030-05-31'),('2024-05-01','2024-05-31'),('2025-06-01','2025-06-30')])
def test_ordered_event_interval_still_requires_the_source_month_and_year(lower,upper):
    claim=spec('MPOR-2025-VREX-DISPOSAL')
    claim.update(event_date_lower=lower,event_date_upper=upper,valid_date=upper)
    with pytest.raises(ValueError,match='source month|publication'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


def test_correct_quarter_requires_source_year_and_exact_registered_outer_quarter():
    claim=spec('MPOR-2025-INTERNAL-FEED')
    claim.update(event_date_lower='2024-10-01',event_date_upper='2024-12-31',valid_date='2024-12-31')
    with pytest.raises(ValueError,match='source month/quarter/year'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


def test_unspecified_end_of_year_phrase_is_not_an_exact_quarter_event_interval():
    claim=spec('MPOR-2025-MAGNET-COMMISSIONING')
    assert claim['event_date_lower'] is None and claim['event_date_upper'] is None
    assert 'At the end of 2025' in claim['quote']
    claim.update(event_date_lower='2025-10-01',event_date_upper='2025-12-31')
    with pytest.raises(ValueError,match='explicit source month/quarter/year'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)


def test_monetary_comparative_cannot_be_relabelled_to_another_printed_year_or_unit():
    claim=spec('MPOR-2025-REAGENT-PURCHASES-2025');claim.update(reporting_period_end='2024-12-31',valid_date='2024-12-31')
    with pytest.raises(ValueError,match='reported year'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)
    claim=spec('MPOR-2025-REAGENT-PURCHASES-2025');claim['native_unit']='tonnes'
    with pytest.raises(ValueError,match='physical supply'):
        original_claim(claim,SOURCES,CONFIG['source_public_dates'],ROOT)
