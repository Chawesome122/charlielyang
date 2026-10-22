"""No future comparative may enter a historical issuer-guidance baseline."""
import pytest
from weaponized.forecast.reported_guidance import guidance_comparison


BASE=dict(origin='2026-05-14',target_start='2026-04-01',target_end='2026-06-30',outcome_public_date='2026-08-13',
          input_public_dates=['2026-05-14'],baseline=100,actual=120,lower=14,upper=16,
          range_kind='growth_percent',native_unit='USD_thousands')


def test_issuer_range_miss_and_point_convention_are_separate():
    r=guidance_comparison(**BASE)
    assert r['translated_guidance_lower']==pytest.approx(114)
    assert r['translated_guidance_upper']==pytest.approx(116)
    assert r['midpoint_error']==pytest.approx(-5)
    assert r['persistence_error']==-20 and not r['realized_value_inside_stated_range']
    assert not r['statistical_skill_established'] and not r['interval_is_confidence_or_prediction_interval']


@pytest.mark.parametrize('change',[{'input_public_dates':['2026-08-13']},{'outcome_public_date':'2026-10-12'},
                                  {'target_end':'2026-12-31'},{'origin':'2026-03-31'},
                                  {'lower':17,'upper':16},{'baseline':0},{'actual':float('nan')},
                                  {'range_kind':'margin_level_percent'},{'native_unit':'metric_tonnes'}])
def test_invalid_vintage_or_units_rejected(change):
    with pytest.raises(ValueError):guidance_comparison(**(BASE|change))


def test_margin_levels_and_percentage_point_errors():
    r=guidance_comparison(**(BASE|dict(baseline=20.1,actual=25.3,lower=20,upper=22,
                                     range_kind='margin_level_percent',native_unit='percent')))
    assert r['translated_guidance_lower']==20 and r['translated_guidance_upper']==22
    assert r['midpoint_error']==pytest.approx(-4.3)
    assert r['persistence_error']==pytest.approx(-5.2) and r['error_unit']=='percentage_points'


def test_later_outcome_changes_errors_but_not_forecast_or_baseline():
    a=guidance_comparison(**BASE);b=guidance_comparison(**(BASE|dict(actual=105)))
    for k in ['guidance_midpoint','baseline_persistence','translated_guidance_lower','translated_guidance_upper']:
        assert a[k]==b[k]
    assert a['midpoint_error']!=b['midpoint_error']
