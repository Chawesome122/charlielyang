"""Adversarial integration audit authored separately from module implementations.

These tests use explicitly synthetic fixtures or re-evaluate archived scenario
policies. They do not validate industrial recipes, causal identification, or a
continuous-state equilibrium.
"""
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pandas as pd
import pytest

from weaponized.forecast.origins import run_backtests, outcome_eligibility
from weaponized.forecast.scoring import probability_summary, summarize_thresholds, persistence_times, time_dependent_brier
from weaponized.io.vintages import select_asof
from weaponized.rare_earths.lp import Commodity, Facility, Route, ExternalFeed, Demand, Inventory, Network, solve_network, Activity
from weaponized.rare_earths.resilience import fixture_ab, make_physical_bridge, nminus1_resilience
from weaponized.rare_earths.projects import ProjectSnapshot, quarter_index
from weaponized.rare_earths.ramps import RampSpec
from weaponized.rare_earths.simulate import simulate_projects
from weaponized.rare_earths.transitions import TransitionModel
from weaponized.game.primitives import GameParameters, dynamics, payoffs
from weaponized.game.hjb import StateGrid
from weaponized.game.stability import feedback_stationary_point, interpolated_policy

ROOT=Path(__file__).resolve().parents[1]


def test_later_correction_and_tombstone_never_rewrite_earlier_information():
    rows=pd.DataFrame([
        {'observation_id':'a','record_version_id':'1','info_public_date':'2020-01-01','valid_date':'2019-01-01','value':10,'withdrawn':False},
        {'observation_id':'a','record_version_id':'2','info_public_date':'2024-01-01','valid_date':'2019-01-01','value':100,'withdrawn':False},
        {'observation_id':'a','record_version_id':'3','info_public_date':'2025-01-01','valid_date':'2019-01-01','value':100,'withdrawn':True},
    ])
    assert select_asof(rows,'2023-12-31').value.tolist()==[10]
    assert select_asof(rows,'2024-12-31').value.tolist()==[100]
    assert select_asof(rows,'2025-12-31').empty
    with pytest.raises(ValueError,match='freeze'):select_asof(rows,'2026-10-12')


@pytest.mark.parametrize('metadata',[
    {},
    {'vintage_id':'test','prediction_as_of':'2020-12-31','input_info_public_dates':['2024-01-01']},
    {'vintage_id':'test','prediction_as_of':'2024-01-01','input_info_public_dates':['2019-01-01']},
    {'vintage_id':'test','prediction_as_of':'2020-12-31','input_info_public_dates':[None]},
])
def test_registered_origin_key_cannot_authorize_future_training_data(metadata):
    called=[]
    def forbidden():
        called.append(True)
        raise AssertionError('Ineligible forecast callback was invoked')
    key=('2020-12-31',2)
    registry={key:{'prediction':forbidden,'outcome':forbidden,**metadata}}
    report=run_backtests(registry,[(date(2020,12,31),2)],{key:date(2023,3,1)},{},{})
    assert not report[0]['scoreable'] and not called
    assert report[0]['reason'] in {'prediction_vintage_not_auditable','prediction_vintage_leakage'}


def test_eligible_vintage_can_score_but_unreleased_or_future_outcome_cannot():
    origin=date(2020,12,31); key=(origin.isoformat(),2)
    record={'vintage_id':'SYNTHETIC-origin-2020','prediction_as_of':origin,
            'input_info_public_dates':[date(2019,12,31),origin],
            'prediction':lambda:[.8,.2],'outcome':lambda:[1,0]}
    result=run_backtests({key:record},[(origin,2)],{key:date(2023,3,1)},{},{'coin':lambda r:[.5,.5]})[0]
    assert result['scoreable'] and result['model']['brier']==pytest.approx(.04)
    assert result['model']['brier']<result['baselines']['coin']['brier']
    assert not outcome_eligibility(date(2020,12,31),6,date(2026,10,11))['scoreable']
    assert not outcome_eligibility(origin,2,date(2026,10,12))['scoreable']


def test_finite_zero_draw_count_does_not_certify_monte_carlo_precision():
    small=probability_summary([False])
    assert small['probability']==0 and small['mc_wilson_95'][1]>.5
    assert not small['mc_tolerance_met']
    assert probability_summary(np.zeros(10000,dtype=bool))['mc_tolerance_met']
    assert not probability_summary(np.zeros(10000,dtype=bool),effective_sample_size=1)['mc_tolerance_met']
    with pytest.raises(ValueError):probability_summary([np.nan])
    with pytest.raises(ValueError):probability_summary([2])


def test_persistence_distinguishes_start_and_recognition_and_censoring():
    # First brief threshold crossing fails. The only persistent episode starts at
    # quarter 12 and is recognized at 15; those are different forecast estimands.
    service=np.array([[.8,.8,.7,.8,.8,.8,.8]])
    q=np.arange(9,16)
    start,recognition=persistence_times(service,q,.75)
    assert start.tolist()==[12] and recognition.tolist()==[15]
    panel=SimpleNamespace(served_fraction=service,quarters=q)
    result=summarize_thresholds(panel,[12],thresholds=[.75])[0]
    assert result['start_by_target']['probability']==1
    assert result['recognized_by_target']['probability']==0
    with pytest.raises(ValueError,match='right-censored'):summarize_thresholds(panel,[13],thresholds=[.75])


def test_competing_event_is_observed_zero_not_informative_censor():
    # n=4: target event at1 with G(1-)=.8, competing event at2 with
    # G(2-)=.5, at-risk at4 with G(3)=.5, censored at2 excluded by IPCW.
    # Contributions for p=.25: .75²/.8, .25²/.5, .25²/.5, zero.
    survival=lambda t,left:.8 if t==1 else .5
    result=time_dependent_brier([.25]*4,[1,2,4,2],[1,2,0,0],3,1,survival)
    assert result['known_status_n']==3
    assert result['ipcw_brier']==pytest.approx((.75**2/.8+.25**2/.5+.25**2/.5)/4)


def stock_network(origin_groups=frozenset()):
    return Network((Commodity('magnet','qualified_magnet',{'Nd':1},origin_groups),),
                   (Facility('bloc'),),(),(),(),(Demand('d','bloc',{'magnet':1},1,1),),
                   opening_inventory={('bloc','magnet'):Inventory(1,origin_groups)},
                   storage_limits={('bloc','magnet'):1},label='SYNTHETIC one-time opening stock')


def test_opening_stock_is_conserved_over_entire_horizon_and_china_tag_removed():
    result=solve_network(stock_network(),quarters=[1,2,3])
    assert sum(result.delivered.values())<=1+1e-8
    assert result.external_feed=={}
    removed=solve_network(stock_network(frozenset({'CHN'})),quarters=[1,2,3],failed_groups={'CHN'})
    assert sum(removed.delivered.values())==pytest.approx(0)
    with pytest.raises(ValueError,match='inventor'):make_physical_bridge(stock_network())


def test_transport_supplier_outage_removes_route_even_with_foreign_facilities():
    network=Network((Commodity('magnet','qualified_magnet',{'Nd':1}),),
        (Facility('foreign_origin',frozenset({'B'})),Facility('bloc')),
        (), (Route('only_transport','foreign_origin','bloc','magnet',1,frozenset({'logistics_A'})),),
        (ExternalFeed('finite_import','foreign_origin','magnet',1,frozenset({'B'})),),
        (Demand('d','bloc',{'magnet':1},1,1),),label='SYNTHETIC logistics ownership outage')
    assert solve_network(network).served_fraction_by_quarter[0]==pytest.approx(1,abs=1e-8)
    outage=nminus1_resilience(network,candidate_suppliers=['logistics_A'])
    assert outage.served_fraction.tolist()==[0]
    empty_feed=replace(network,feeds=())
    assert solve_network(empty_feed).served_fraction_by_quarter[0]==pytest.approx(0)


def test_stateless_physical_bridge_interoperates_with_project_simulation():
    network=fixture_ab();origin=date(2020,12,31);first=quarter_index('2021Q1')
    projects=[ProjectSnapshot('magnet_'+s,s,s,'magnet','O',8,origin,quarter_index('2019Q1')) for s in ('A','B')]
    ramps={'magnet_A':RampSpec(160,kind='step'),'magnet_B':RampSpec(140,kind='step')}
    streams={name:np.random.default_rng(i) for i,name in enumerate(('projects','parameters','common_shocks','process_yields'))}
    panel=simulate_projects(projects,TransitionModel({}),ramps,
            {'origin':origin,'quarters':[first,first+1],'physical_bridge':make_physical_bridge(network),'provenance':'SYNTHETIC'},streams,2)
    assert np.allclose(panel.served_fraction,1,atol=1e-8)
    assert np.allclose(panel.raw_coverage,75/70)


def test_nonsmooth_feedback_knot_cannot_be_certified_stable_by_central_secant():
    grid=StateGrid(5);p=GameParameters(g_c=.1,g_u=.1,delta_c=.1,delta_u=.1,beta_c=0,beta_u=0)
    # Right of m=.5 this policy has du/dm=2, so m_dot derivative is +kappa.
    u=np.clip(.5+2*np.abs(grid.states[:,2]-.5),0,1);c=np.full(grid.count,.5)
    result=feedback_stationary_point(grid,u,c,p,guess=np.full(4,.5))
    policy=interpolated_policy(grid,u,c)
    test_state=np.array([.5,.5,.5001,.5]);ut,ct=policy(test_state)
    assert dynamics(test_state,ut,ct,p)[2]>0
    assert result['verified_stationary_point']
    assert result['locally_stable'] is not True
    assert result.get('stability_status')=='inconclusive_at_interpolation_knot'


def test_archived_scenario_policy_independent_dense_unilateral_deviations():
    """Dense controls use direct neighboring values, bypassing BR helper code."""
    archive=ROOT/'outputs/scenario/game/adaptation_positive_n17_mid.npz'
    data=np.load(archive);axis=data['axis'];size=len(axis);h=axis[1]-axis[0]
    grid=StateGrid(size);p=GameParameters()
    u,c=data['u'].ravel(),data['c'].ravel()
    values=[data['value_u'].reshape(grid.shape),data['value_c'].reshape(grid.shape)]
    rng=np.random.default_rng(1776)
    chosen=np.r_[0,grid.count-1,rng.choice(grid.count,32,replace=False)]
    controls=np.linspace(0,1,2049)
    for node in chosen:
        coords=np.unravel_index(node,grid.shape);state=grid.states[node]
        for player in (0,1):
            us=controls if player==0 else np.full_like(controls,u[node])
            cs=controls if player==1 else np.full_like(controls,c[node])
            drift=dynamics(np.broadcast_to(state,(len(controls),4)),us,cs,p)
            generator_value=np.zeros(len(controls))
            for dim in range(4):
                if coords[dim]+1<size:
                    neighbor=list(coords);neighbor[dim]+=1
                    generator_value+=np.maximum(drift[:,dim],0)*(values[player][tuple(neighbor)]-values[player][coords])/h
                if coords[dim]>0:
                    neighbor=list(coords);neighbor[dim]-=1
                    generator_value+=np.maximum(-drift[:,dim],0)*(values[player][tuple(neighbor)]-values[player][coords])/h
            reward=payoffs(np.broadcast_to(state,(len(controls),4)),us,cs,p)[player]
            residual=reward+generator_value-(p.rho_u if player==0 else p.rho_c)*values[player][coords]
            assert residual.max()<1e-7
