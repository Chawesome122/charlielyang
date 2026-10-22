"""Evaluate a reported nonprobabilistic range, distinct from model forecasting."""
from datetime import date
import math


def guidance_comparison(*, origin, target_start, target_end, outcome_public_date,
                        input_public_dates, baseline, actual, lower, upper,
                        range_kind, native_unit, freeze='2026-10-11'):
    for d in [origin,target_start,target_end,outcome_public_date,freeze,*input_public_dates]:date.fromisoformat(d)
    if not target_start<=origin<target_end<=outcome_public_date<=freeze:
        raise ValueError('Expected within-quarter guidance, later observed outcome and admissible freeze')
    if not input_public_dates or any(d>origin for d in input_public_dates):
        raise ValueError('Guidance evaluation inputs contain future source information')
    if not all(math.isfinite(v) for v in [baseline,actual,lower,upper]) or baseline<0 or actual<0 or lower>upper:
        raise ValueError('Invalid source values or reversed guidance range')
    if range_kind=='growth_percent' and native_unit=='USD_thousands':
        if lower < -100 or baseline<=0:raise ValueError('Growth requires positive baseline and nonnegative implied revenue')
        lo,hi=baseline*(1+lower/100),baseline*(1+upper/100)
    elif range_kind=='margin_level_percent' and native_unit=='percent':
        if not 0<=lower<=upper<=100 or baseline>100 or actual>100:raise ValueError('Margin outside percentage domain')
        lo,hi=lower,upper
    else:raise ValueError('Explicit range type/unit agreement required')
    midpoint=(lo+hi)/2
    return dict(origin=origin,target_start=target_start,target_end=target_end,outcome_public_date=outcome_public_date,
                native_unit=native_unit,error_unit='percentage_points' if native_unit=='percent' else native_unit,baseline_persistence=baseline,actual=actual,
                translated_guidance_lower=lo,translated_guidance_upper=hi,guidance_midpoint=midpoint,
                realized_value_inside_stated_range=lo<=actual<=hi,
                midpoint_error=midpoint-actual,midpoint_absolute_error=abs(midpoint-actual),
                persistence_error=baseline-actual,persistence_absolute_error=abs(baseline-actual),
                midpoint_improves_on_persistence=abs(midpoint-actual)<abs(baseline-actual),
                maximum_input_public_date=max(input_public_dates),
                interval_is_confidence_or_prediction_interval=False,
                observation_is_prequarter_ex_ante_forecast=False,
                structural_model_accuracy_established=False,statistical_skill_established=False,
                outcome_vintage='later supplied issuer release; historical byte identity uncertified',
                interpretation='within-quarter issuer guidance; midpoint is an evaluation convention, not an issuer point forecast')
