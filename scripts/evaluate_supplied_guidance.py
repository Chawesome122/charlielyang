"""One target quarter of real issuer guidance; no general forecasting-skill claim."""
import json
from pathlib import Path

import pandas as pd

from weaponized.forecast.reported_guidance import guidance_comparison

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/supplied_evidence'
OUT=ROOT/'outputs/empirical/supplied_evidence'


def main():
    claims=pd.read_csv(DATA/'claims.csv').set_index('variable')
    smic=pd.read_csv(DATA/'smic_quarterly_versions.csv')
    source1='UP-SC-SMIC-Q12026-EARNINGS';source2='UP-SC-SMIC-Q22026-EARNINGS'
    rev1=smic[smic.source_id.eq(source1)&smic.variable.eq('total_revenue')&smic.period_end.eq('2026-03-31')].iloc[0]
    rev2=smic[smic.source_id.eq(source2)&smic.variable.eq('total_revenue')&smic.period_end.eq('2026-06-30')].iloc[0]
    rows=[]
    for label,base,actual,lo,hi,kind,unit in [
        ('revenue',rev1,rev2,claims.loc['smic_q2_revenue_growth_guidance_lower'],claims.loc['smic_q2_revenue_growth_guidance_upper'],'growth_percent','USD_thousands'),
        ('gross_margin',claims.loc['smic_1Q26_gross_margin'],claims.loc['smic_2Q26_gross_margin'],claims.loc['smic_q2_margin_guidance_lower'],claims.loc['smic_q2_margin_guidance_upper'],'margin_level_percent','percent')]:
        r=guidance_comparison(origin=lo.info_public_date,target_start='2026-04-01',target_end='2026-06-30',
                              outcome_public_date=actual.info_public_date,input_public_dates=[base.info_public_date,lo.info_public_date,hi.info_public_date],
                              baseline=float(base.value),actual=float(actual.value),lower=float(lo.value),upper=float(hi.value),range_kind=kind,native_unit=unit)
        r.update(variable=label,origin_source=source1,outcome_source=source2,
                 origin_source_sha256=base.source_sha256,outcome_source_sha256=actual.source_sha256,
                 baseline_locator=base.locator,outcome_locator=actual.locator,
                 guidance_lower_locator=lo.locator,guidance_upper_locator=hi.locator,
                 issuer_guidance_native_lower=float(lo.value),issuer_guidance_native_upper=float(hi.value),
                 issuer_guidance_kind=kind,seasonal_baseline_omitted_reason='same-quarter prior-year comparison not independently available in the selected source archive at guidance issuance; later comparative not backdated')
        rows.append(r)
    pd.DataFrame(rows).to_csv(OUT/'smic_guidance_evaluation.csv',index=False)
    result=dict(passed=all(r['maximum_input_public_date']<=r['origin']<r['target_end']<=r['outcome_public_date']<='2026-10-11' for r in rows),
                evidence_class='actual_within_quarter_issuer_guidance_evaluation',target_quarters=1,related_outcomes=2,
                realized_values_in_stated_ranges=sum(r['realized_value_inside_stated_range'] for r in rows),
                midpoint_improves_on_persistence_count=sum(r['midpoint_improves_on_persistence'] for r in rows),
                interval_probability_coverage_claimed=False,statistical_skill_established=False,
                structural_research_model_evaluated=False,blueprint_6_12_24_month_forecasts_evaluated=False,
                empirical_magnet_service_forecast=False,
                scope='Two correlated financial outcomes in one quarter; no significance/skill inference, quality-adjusted price or technical capability claim')
    (OUT/'guidance_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Issuer guidance evaluation leaks source information')


if __name__=='__main__':main()
