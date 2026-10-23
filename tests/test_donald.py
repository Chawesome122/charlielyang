"""Guard the scientific distinctions that make the new report usable."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.io.supplied_evidence import asof_supplied, extract_claim, incorporated_report_link, source_pages, stated_event_window
from weaponized.rare_earths.donald import GRADE_BASIS, OXIDES, conditional_reec_composition, nested_coefficients, partial_recovery_lp
from weaponized.rare_earths.materials import oxide_element_fraction

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def coefficients():
    return nested_coefficients(.045,{'Nd':.002,'Pr':.00056,'Dy':.00041,'Tb':.000064},
                               {'Nd':.92,'Pr':.92,'Dy':.88,'Tb':.88},grade_basis=GRADE_BASIS)


def test_nested_hm_denominator_not_bulk_ore(coefficients):
    nd=next(r for r in coefficients if r['element']=='Nd')
    expected=.045*.002*.92*oxide_element_fraction('Nd2O3','Nd')
    assert nd['recovered_element_t_per_ore_t']==pytest.approx(expected)
    wrong=.002*.92*oxide_element_fraction('Nd2O3','Nd')
    assert wrong/expected==pytest.approx(1/.045)
    for r in coefficients:
        assert r['input_element_t_per_ore_t']==pytest.approx(r['recovered_element_t_per_ore_t']+r['residual_element_t_per_ore_t'])


@pytest.mark.parametrize('basis',['oxide_mass_per_ore_mass','percent_of_TREO','unknown'])
def test_wrong_denominator_rejected(basis):
    with pytest.raises(ValueError,match='heavy-mineral denominator'):
        nested_coefficients(.045,dict.fromkeys(OXIDES,.01),dict.fromkeys(OXIDES,.9),grade_basis=basis)


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True,1.01])
def test_recovery_must_be_identified_finite_fraction(bad):
    recovery=dict.fromkeys(OXIDES,.9);recovery['Dy']=bad
    with pytest.raises(ValueError):nested_coefficients(.045,dict.fromkeys(OXIDES,.01),recovery,grade_basis=GRADE_BASIS)


def test_shared_feed_is_not_four_independent_ore_streams(coefficients):
    r=partial_recovery_lp(coefficients,1000,250)
    assert r['passed'] and r['throughput_tonnes']==250
    for c in coefficients:
        assert r['output_element_tonnes'][c['element']]==pytest.approx(250*c['recovered_element_t_per_ore_t'])
        assert r['residual_or_unrecovered_element_tonnes'][c['element']]>=0
    assert r['primal_dual_gap_tonnes']<1e-12 and r['delivered_magnet_service'] is None


@pytest.mark.parametrize('kwargs',[{'feed_capacity':0,'plant_feed_capacity':1000},
    {'feed_capacity':1000,'plant_feed_capacity':0},
    {'feed_capacity':1000,'plant_feed_capacity':1000,'route_open':False},
    {'feed_capacity':1000,'plant_feed_capacity':1000,'supplier_removed':True}])
def test_no_feed_no_route_or_owner_outage_all_elements_zero(coefficients,kwargs):
    r=partial_recovery_lp(coefficients,**kwargs)
    assert r['passed'] and r['throughput_tonnes']==0 and not any(r['output_element_tonnes'].values())


@pytest.mark.parametrize('capacity',[None,float('inf'),float('nan'),-1,True])
def test_no_unbounded_or_missing_feed(coefficients,capacity):
    with pytest.raises(ValueError):partial_recovery_lp(coefficients,capacity,1000)


def test_element_creation_rejected(coefficients):
    rows=copy.deepcopy(coefficients);rows[0]['recovered_element_t_per_ore_t']=2*rows[0]['input_element_t_per_ore_t']
    with pytest.raises(ValueError,match='creates'):partial_recovery_lp(rows,1,1)


def test_element_split_required_and_joint_shares_close():
    with pytest.raises(ValueError,match='explicit Nd/Pr/Dy/Tb'):
        conditional_reec_composition(.606,{'NdPr':.177,'Dy':.0267,'Tb':.0041})
    with pytest.raises(ValueError,match='exceed'):
        conditional_reec_composition(.606,dict.fromkeys(OXIDES,.3))
    rows=conditional_reec_composition(.606,{'Nd':.1385,'Pr':.0385,'Dy':.0267,'Tb':.0041})
    assert next(r for r in rows if r['element']=='Dy')['conditional_oxide_t_per_reec_t']==pytest.approx(.606*.0267)
    assert all(r['annual_feed_available'] is None and not r['moisture_basis_certified'] for r in rows)


def test_exact_accession_not_reused_exhibit_basename():
    parent='https://www.sec.gov/Archives/edgar/data/1385849/parent/efr.htm'
    wanted='https://www.sec.gov/Archives/edgar/data/1385849/000106299326001182/exhibit99-2.htm'
    wrong=wanted.replace('000106299326001182','000106299323000001')
    with pytest.raises(ValueError,match='Full incorporated report URL'):
        incorporated_report_link(f'<a href="{wrong}">Sheep Mountain report</a>'.encode(),parent,wanted)
    assert incorporated_report_link(f'<a href="{wanted}">Donald report</a>'.encode(),parent,wanted)=='Donald report'
    assert incorporated_report_link(b'<a href="../r/exhibit99-2.htm">Correct relative</a>',parent,'https://www.sec.gov/Archives/edgar/data/1385849/r/exhibit99-2.htm')=='Correct relative'


def test_short_quarter_does_not_become_an_exact_event_day():
    assert stated_event_window('Q3 2026')==('2026-07-01','2026-09-30')
    assert stated_event_window('Q1 2028')==('2028-01-01','2028-03-31')
    with pytest.raises(ValueError):stated_event_window('Q5 2026')


@pytest.fixture(scope='module')
def original_claims():
    sources={s['source_id']:s for s in json.loads((ROOT/'metadata/user_supplied_sources.json').read_text())}
    specs=[c for c in json.loads((ROOT/'codebooks/supplied_evidence.json').read_text())['claims'] if c['variable'].startswith('donald_')]
    pages={s:source_pages(ROOT,sources[s]) for s in {c['source_id'] for c in specs}}
    return specs,sources,pages


def test_fid_target_miss_has_no_lookahead(original_claims):
    specs,sources,pages=original_claims
    rows=[extract_claim(pages[c['source_id']],c,sources[c['source_id']]) for c in specs]
    f=pd.DataFrame(rows)
    assert asof_supplied(f,'2026-02-25').empty
    assert 'donald_no_fid_2026H1' not in set(asof_supplied(f,'2026-06-30').variable)
    available=asof_supplied(f,'2026-08-05').set_index('variable')
    assert available.loc['donald_no_fid_2026H1','event_kind']=='observed'
    assert available.loc['donald_fid_initial_target','event_kind']=='planned'
    assert available.loc['donald_fid_revised_target','event_kind']=='planned'
    assert available.loc['donald_ownership_2026H1','value']==12.7
    assert not available.empirical_service_identified.any()


def test_reserve_row_header_and_total_cell_cannot_drift(original_claims):
    specs,sources,pages=original_claims
    c=next(c for c in specs if c['variable']=='donald_reserve_pr')
    wrong=c|dict(value=.057) # Nearby proven-reserve number is not total reserve.
    with pytest.raises(ValueError,match='named source cell'):extract_claim(pages[c['source_id']],wrong,sources[c['source_id']])
    wrong=c|dict(header_pattern='Table 1.2 Donald Mineral Resource')
    with pytest.raises(ValueError):extract_claim(pages[c['source_id']],wrong,sources[c['source_id']])


def test_joint_contained_input_mass_cannot_exceed_native_ore(coefficients):
    rows=copy.deepcopy(coefficients)
    for r in rows:
        r['input_element_t_per_ore_t']=.3
        r['recovered_element_t_per_ore_t']=.2
    # Each element individually loses mass, yet four input fractions sum to 1.2.
    with pytest.raises(ValueError,match='Joint contained-element input'):
        partial_recovery_lp(rows,1,1)
