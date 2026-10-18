from datetime import date
import math
import numpy as np
import pandas as pd
import pytest
from weaponized.opacity import aggregate_scores, spoi_daily, quarterly_spoi, opacity_regression_gate
from weaponized.opacity.coding import *
from weaponized.opacity.events import event_score, known_rows
from weaponized.opacity.obligations import obligation_score
from weaponized.opacity.reliability import weighted_kappa, reliability_report


def coverage():
    return pd.DataFrame([{'coverage_id':'syn-coverage','kind':'coverage','indicator':'ALL',
                          'info_public_date':'2024-01-01','valid_from':'2024-01-01',
                          'valid_until':'2026-12-31','adjudicated':True,'source_id':'SYNTHETIC'}])


def event(**kwargs):
    row = {'event_id':'syn-event','event_type':'new_policy','publication_date':'2025-01-01',
           'info_public_date':'2025-01-01','effective_date':'2025-01-01','material':True,
           'substantive':True,'source_id':'SYNTHETIC'}
    row.update(kwargs)
    return pd.DataFrame([row])


@pytest.mark.parametrize('vector,expected',[
    ([1,2,4,4,1,3,1,2,2,3],57.41666666666667),
    ([0,1,2,1,0,1,0,0,1,1],16.75)])
def test_exact_blueprint_synthetic_scores(vector, expected):
    result=aggregate_scores(dict(zip(CODES,vector)))
    assert result['daily_valid']
    assert result['spoi']==pytest.approx(expected)


def test_pillar_gate_and_weights_are_not_redistributed():
    s=dict(zip(CODES,[1,2,4,4,1,3,1,2,2,3]))
    s['O1']=s['O2']=None
    result=aggregate_scores(s)
    assert result['daily_valid']
    assert result['disclosure']==pytest.approx(8/12)
    s['O3']=None
    assert not aggregate_scores(s)['daily_valid']
    s=dict(zip(CODES,[1]*10)); s['O5']=s['O7']=None
    assert not aggregate_scores(s)['daily_valid']


@pytest.mark.parametrize('function,values,expected',[
    (score_lateness,[0,1,30,31,90,91,180,181],[0,1,1,2,2,3,3,4]),
    (score_lead_time,[-1,0,6,7,29,30,59,60,89,90],[4,4,4,3,3,2,2,1,1,0]),
    (score_missing_fields,[0,.05,.051,.15,.151,.30,.301,.50,.501],[0,0,1,1,2,2,3,3,4]),
    (score_availability,[1,.9,.899,.7,.699,.5,.499,.25,.249],[0,0,1,1,2,2,3,3,4]),
    (score_absent_releases,[0,.001,.1,.101,.25,.251,.5,.501],[0,1,1,2,2,3,3,4])])
def test_rubric_boundaries(function, values, expected):
    assert [function(v) for v in values] == expected


def test_no_event_rule_requires_adjudicated_coverage():
    for code in ['O4','O6','O10']:
        assert event_score(code,pd.DataFrame(),coverage(),date(2025,5,1)).score==0
        result=event_score(code,pd.DataFrame(),pd.DataFrame(),date(2025,5,1))
        assert result.score is None and result.status=='researcher_missing'


def test_policy_memory_is_left_open_and_future_information_excluded():
    e=event()
    assert event_score('O4',e,coverage(),date(2025,3,31)).score==4
    assert event_score('O4',e,coverage(),date(2025,4,1)).score==0
    assert event_score('O4',event(info_public_date='2025-02-01'),coverage(),date(2025,1,10)).score==0
    assert event_score('O4',event(effective_date=None),coverage(),date(2025,1,10)).status=='researcher_missing'


def test_material_reversal_announced_before_effective_persists_later_clock():
    e=event(event_type='adverse_reversal',effective_date='2025-02-01')
    assert event_score('O6',e,coverage(),date(2025,1,1)).score==2
    assert event_score('O6',e,coverage(),date(2025,5,1)).score==2
    assert event_score('O6',e,coverage(),date(2025,5,2)).score==0
    assert event_score('O6',e,coverage(),date(2024,12,31)).score==0


def test_amendments_are_public_effective_deduplicated_material_only():
    e=event(event_type='amendment',effective_date='2025-02-01',intervention_id='one')
    e=pd.concat([e,e.assign(event_id='other_agency'),e.assign(event_id='typo',material=False,intervention_id='typo')])
    assert event_score('O10',e,coverage(),date(2025,1,15)).score==0
    assert event_score('O10',e,coverage(),date(2025,2,1)).score==1
    assert event_score('O10',e,coverage(),date(2025,5,2)).score==0


def test_current_rule_persistence_end_and_weight_vintage():
    e=event(event_type='legal_rule',explicit_scope_fields=3,end_date='2025-06-01')
    assert event_score('O5',e,coverage(),date(2025,5,1)).score==1
    assert event_score('O5',e,coverage(),date(2025,6,1)).status=='not_applicable'
    with pytest.raises(ValueError):
        event_score('O5',e.assign(frozen_exposure_weight=1,weight_info_public_date='2025-02-01'),coverage(),date(2025,5,1),legal_aggregation='exposure_weighted')


def test_conflict_materiality_and_resolution_memory():
    e=event(event_type='conflict',materiality='material',resolution_date='2025-01-15',resolution_info_public_date='2025-01-15')
    assert event_score('O7',e,coverage(),date(2025,1,2)).score==2
    assert event_score('O7',e,coverage(),date(2025,4,14)).score==2
    assert event_score('O7',e,coverage(),date(2025,4,15)).score==0
    assert score_conflicts(0,1,True)==4
    assert score_conflicts(0,2)==3
    assert score_conflicts(0,3)==4


def obligation(**updates):
    row={'obligation_id':'syn-release','info_public_date':'2024-12-01','due_date':'2025-01-01',
         'observation_end_date':'2025-04-01','next_due_date':'2025-04-01',
         'indicators':'O1;O2;O3;O8;O9','denominator_source_id':'SYNTHETIC-DUTY',
         'release_date':'2025-01-10','release_info_public_date':'2025-01-10',
         'missing_required_fields':1,'required_fields':10,'available_license_metrics':2,
         'expected_license_metrics':5,'classifiable_throughput':7,'total_documented_throughput':10,
         'measurement_unit':'tonne_REO','measurement_basis':'frozen_official_REO_output_series'}
    row.update(updates);return pd.DataFrame([row])


def test_obligation_lateness_completeness_and_denominators():
    o=obligation()
    assert obligation_score('O1',o,date(2025,1,11)).score==1
    assert obligation_score('O2',o,date(2025,1,11)).score==1
    assert obligation_score('O3',o,date(2025,1,11)).score==3
    assert obligation_score('O9',o,date(2025,1,11)).score==1
    assert obligation_score('O1',o,date(2025,1,9)).status=='researcher_missing'
    assert obligation_score('O1',o,date(2025,4,1)).status=='not_applicable'
    assert obligation_score('O9',obligation(total_documented_throughput=0),date(2025,1,11)).status=='not_applicable'


def test_no_obligation_not_highest_opacity_and_checkpoint_grace():
    for code in ['O1','O2','O3','O8','O9']:
        assert obligation_score(code,pd.DataFrame(),date(2025,2,1)).status=='not_applicable'
    assert obligation_score('O8',obligation(),date(2025,1,30)).status=='not_applicable'
    assert obligation_score('O8',obligation(),date(2025,1,31)).score==0
    assert obligation_score('O8',obligation(release_date=None,release_info_public_date=None),date(2025,1,31)).status=='researcher_missing'
    o=obligation(release_date=None,release_info_public_date=None,affirmatively_absent=True,absence_verified_on='2025-01-31')
    assert obligation_score('O8',o,date(2025,1,31)).score==4
    assert obligation_score('O1',o,date(2025,1,31)).score==1


def test_historical_versions_select_latest_public_not_latest_actual():
    old={'event_id':'v','record_version_id':'1','info_public_date':'2024-01-01','effective_date':'2024-01-01'}
    new={**old,'record_version_id':'2','info_public_date':'2025-01-01','effective_date':'2023-01-01'}
    assert known_rows(pd.DataFrame([old,new]),date(2024,6,1))==[old]
    assert known_rows(pd.DataFrame([old,new]),date(2025,6,1))==[new]


def test_quarter_coverage_uses_calendar_not_present_rows():
    days=pd.date_range('2025-01-01','2025-03-31')
    rows=[]
    for d in days:
        row={'date':d,'legal_events':0,**dict(zip(CODES,[0]*10))}
        row.update(aggregate_scores(row));rows.append(row)
    d=pd.DataFrame(rows)
    assert quarterly_spoi(d.iloc[:72]).iloc[0]['quarter_valid']
    assert quarterly_spoi(d.iloc[:72]).iloc[0]['coverage']==.8
    assert not quarterly_spoi(d.iloc[:71]).iloc[0]['quarter_valid']
    with pytest.raises(ValueError): quarterly_spoi(pd.concat([d,d.iloc[:1]]))


def test_daily_integration_keeps_headline_missing():
    daily=spoi_daily(pd.DataFrame(),pd.DataFrame(),coverage(),{},'2025-01-01','2025-03-31')
    assert (daily['O4']==0).all() and (daily['O6']==0).all() and (daily['O10']==0).all()
    assert daily['spoi'].isna().all()
    assert opacity_regression_gate(quarterly_spoi(daily))['status']=='BLOCKED'


def test_reliability_independence_required_and_ci_reproducible():
    assert reliability_report([],[],independent=False)['status']=='BLOCKED'
    a=[0,1,2,3,4]*10;b=[0,1,2,4,4]*10
    assert weighted_kappa(a,a)==pytest.approx(1)
    r=reliability_report(a,b,independent=True,n_bootstrap=100,seed=13)
    assert r['ci_lower']<=r['kappa']<=r['ci_upper']
    assert r==reliability_report(a,b,independent=True,n_bootstrap=100,seed=13)
    assert math.isnan(weighted_kappa([0,0],[0,0]))
    with pytest.raises(ValueError): weighted_kappa([5,0],[0,0])


def test_missing_status_cannot_carry_score():
    with pytest.raises(ValueError): CodedObservation(4,'researcher_missing','not_read')
    with pytest.raises(ValueError): aggregate_scores({'O1':5})


def test_o9_incomparable_stage_units_never_added():
    o=pd.concat([obligation(),obligation(obligation_id='second',measurement_unit='tonne_finished_magnet')])
    assert obligation_score('O9',o,date(2025,1,11)).status=='researcher_missing'


def test_conflict_resolution_cannot_leak_before_its_public_evidence():
    e=event(event_type='conflict',materiality='material',resolution_date='2025-01-15',resolution_info_public_date='2025-07-01')
    assert event_score('O7',e,coverage(),date(2025,4,16)).score==2
    assert event_score('O7',e,coverage(),date(2025,7,1)).score==0


def test_sensitivity_weights_only_aggregate_complete_ten_for_equal_indicator():
    from weaponized.opacity.sensitivity import alternative_weights
    scores=dict(zip(CODES,[1,2,4,4,1,3,1,2,2,3]))
    assert alternative_weights(scores)['equal_ten_indicators']==pytest.approx(57.5)
    scores['O1']=None
    assert math.isnan(alternative_weights(scores)['equal_ten_indicators'])


def test_absence_next_cycle_is_four_when_obligation_remains_unfulfilled():
    o=obligation(release_date=None,release_info_public_date=None,affirmatively_absent=True,
                 absence_verified_on='2025-01-01',observation_end_date='2025-07-01')
    assert obligation_score('O1',o,date(2025,4,1)).score==4


def test_full_daily_to_quarter_synthetic_integration():
    o=obligation(release_date='2025-01-01',release_info_public_date='2025-01-01',
                 missing_required_fields=0,available_license_metrics=5,
                 classifiable_throughput=10)
    e=event(event_type='legal_rule',explicit_scope_fields=4)
    daily=spoi_daily(o,e,coverage(),{},'2025-01-01','2025-03-31')
    assert daily.daily_valid.all()
    assert (daily.spoi==0).all()
    quarter=quarterly_spoi(daily).iloc[0]
    assert quarter.quarter_valid and quarter.coverage==1 and quarter.spoi==0
