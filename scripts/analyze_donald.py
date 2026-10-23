"""Execute source-bound Donald material-basis, schedule and route checks offline."""
from datetime import date
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR','/tmp/weaponized-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from weaponized.io.supplied_evidence import asof_supplied
from weaponized.rare_earths.donald import GRADE_BASIS, OXIDES, conditional_reec_composition, nested_coefficients, partial_recovery_lp
from weaponized.rare_earths.materials import oxide_element_fraction

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/donald'
DIAG=ROOT/'outputs/diagnostics'


def main():
    claims=pd.read_csv(ROOT/'data/processed/supplied_evidence/claims.csv',keep_default_na=False)
    selected=claims[claims.variable.str.startswith('donald_')].copy()
    by=selected.set_index('variable')
    def value(var,unit):
        r=by.loc['donald_'+var]
        if r.native_unit!=unit or r.event_kind not in {'planned','definition','observed'}:
            raise ValueError('Source denominator/unit not bound: '+var)
        return float(r.value)
    hm=value('reserve_hm','percent_total_ore')/100
    grades={e:value('reserve_'+e.lower(),'percent_of_heavy_mineral_component')/100 for e in OXIDES}
    recoveries={e:value('pit_recovery_'+e.lower(),'percent_recovery_to_REEC')/100 for e in OXIDES}
    coefficients=nested_coefficients(hm,grades,recoveries,grade_basis=GRADE_BASIS)
    for r in coefficients:
        e=r['element'].lower()
        r.update(source_id='UP-WM-DONALD-TECHREPORT',source_sha256=by.loc['donald_reserve_hm'].source_sha256,
                 info_public_date=by.loc['donald_reserve_hm'].info_public_date,
                 source_claim_ids=';'.join('SUP:donald_'+v for v in ['reserve_hm','reserve_'+e,'pit_recovery_'+e,'reserve_denominators']),
                 locators='PDF page 28, Table 1.3 total reserve and denominator note; PDF page 119, Table 15.2',
                 available_ore_tonnes=None,annual_output_tonnes=None,delivered_magnet_service=None)
    OUT.mkdir(parents=True,exist_ok=True)
    selected.to_csv(OUT/'source_claims.csv',index=False)
    pd.DataFrame(coefficients).to_csv(OUT/'nested_material_coefficients.csv',index=False)
    shares={e:value('financial_distribution_'+e.lower(),'percent_of_TREO')/100 for e in OXIDES}
    comp=conditional_reec_composition(value('financial_treo_grade','percent_TREO_in_REEC')/100,shares)
    for r in comp:
        r.update(source_id='UP-WM-DONALD-TECHREPORT',source_sha256=by.loc['donald_financial_treo_grade'].source_sha256,
                 info_public_date=by.loc['donald_financial_treo_grade'].info_public_date,
                 source_claim_ids='SUP:donald_financial_treo_grade;SUP:donald_financial_distribution_'+r['element'].lower(),
                 locator='PDF page 187, Table 22.5 and financial-model TREO grade')
    pd.DataFrame(comp).to_csv(OUT/'conditional_reec_composition.csv',index=False)
    checks=[]
    for e,formula in OXIDES.items():
        stated=value('assay_factor_'+e.lower(),'oxide_to_element_mass_ratio')
        exact=1/oxide_element_fraction(formula,e)
        checks.append(dict(check='rounded_assay_factor_'+e,lhs=stated,rhs=exact,tolerance=0.00005,passed=abs(stated-exact)<=0.00005,
                           interpretation='four-decimal source factor agrees with atomic-weight stoichiometry within rounding; not analytical precision'))
    rate=value('plant_dry_rate','dry_metric_tonnes_per_hour');hours=value('plant_design_hours','hours_per_year_design')
    annual=value('plant_design_throughput','million_dry_tonnes_per_year_design')*1e6
    checks.append(dict(check='dry_design_rate_times_design_hours',lhs=rate*hours,rhs=annual,tolerance=1e-8,passed=abs(rate*hours-annual)<1e-8,
                       interpretation='design identity; no calendar-quarter uniform allocation or achieved utilization inferred'))
    current_ef=value('ownership_2026H1','percent_equity_at_reporting_date');astron=value('astron_ownership_2026H1','percent_equity_at_reporting_date')
    checks.append(dict(check='reported_equity_closure_2026H1',lhs=current_ef+astron,rhs=100,tolerance=1e-10,passed=abs(current_ef+astron-100)<1e-10,
                       interpretation='reported current interest; contingent 49 percent is not current equity'))
    # A missed dated milestone is observable without a representative hazard sample.
    original=by.loc['donald_fid_initial_target'];revised=by.loc['donald_fid_revised_target'];negative=by.loc['donald_no_fid_2026H1']
    if original.event_kind!='planned' or revised.event_kind!='planned' or negative.event_kind!='observed':
        raise ValueError('Target/negative-event classifications changed')
    lower_bound=(date.fromisoformat(negative.event_end)-date.fromisoformat(original.event_end)).days
    target_checks=[]
    for origin in ['2026-02-25','2026-02-26','2026-06-30','2026-08-04','2026-08-05','2026-10-11']:
        visible=asof_supplied(selected,origin).set_index('variable')
        missed='donald_no_fid_2026H1' in visible.index and 'donald_fid_initial_target' in visible.index
        known_miss_bound=lower_bound if missed else None
        target_checks.append(dict(origin=origin,original_target_visible='donald_fid_initial_target' in visible.index,
                                  revised_target_visible='donald_fid_revised_target' in visible.index,
                                  no_FID_by_June_30_visible='donald_no_fid_2026H1' in visible.index,
                                  missed_target_lower_bound_days=known_miss_bound,
                                  actual_FID_date=None,first_exit_spell_identified=False,
                                  passed=not missed or origin>=negative.info_public_date))
    pd.DataFrame(target_checks).to_csv(OUT/'target_vintage_checks.csv',index=False)
    target=pd.DataFrame([dict(milestone='financing_and_FID',initial_target_lower=original.event_start,initial_target_upper=original.event_end,
                             initial_public_by=original.info_public_date,initial_claim_id=original.claim_id,
                             observed_no_event_through=negative.event_end,negative_observation_public_by=negative.info_public_date,negative_claim_id=negative.claim_id,
                             revised_target_lower=revised.event_start,revised_target_upper=revised.event_end,revised_public_by=revised.info_public_date,revised_claim_id=revised.claim_id,
                             missed_initial_target_lower_bound_days=lower_bound,delay_upper_bound_days=None,actual_event_date=None,
                             interpretation='documented target miss and revised expectation; not a completed transition or population delay estimate')])
    target.to_csv(OUT/'fid_target_revision.csv',index=False)
    compare=[]
    for e in OXIDES:
        a=by.loc['donald_cross_report_distribution_'+e.lower()];b=by.loc['donald_financial_distribution_'+e.lower()]
        compare.append(dict(element=e,vara_comparative_oxide_percent_of_REO=float(a.value),donald_financial_oxide_percent_of_TREO=float(b.value),
                            numerical_difference_percentage_points=float(b.value)-float(a.value),vara_source_id=a.source_id,vara_source_sha256=a.source_sha256,
                            donald_source_id=b.source_id,donald_source_sha256=b.source_sha256,vara_claim_id=a.claim_id,donald_claim_id=b.claim_id,
                            common_public_by=b.info_public_date,same_sample_certified=False,observed_grade_change_identified=False,
                            interpretation='different disclosed model/assay contexts; preserve versions, do not splice as a physical recipe or infer temporal change'))
    pd.DataFrame(compare).to_csv(OUT/'cross_report_composition_versions.csv',index=False)
    routes=[]
    for gate,var,status,restriction in [
        ('REEC_contract_route','reec_offtake_route','conditional_after_FID','requires_FID_export_permits_and_transport'),
        ('REEC_floor_price','offtake_floor','suspendible','offtake_may_stop_below_floor_with_third_party_sales'),
        ('HMC_coproduct_route','hmc_route','China_and_third_party_processing_right','not_the_REEC_processing_route'),
        ('old_HMC_new_REEC_licence','export_permit','expired_HMC_and_REEC_application_at_report','later_all_major_approval_statement_does_not_prove_each_secondary_permit'),
        ('separate_costed_routes','logistics_routes','planned_not_throughput_evidence','HMC_Zhanjiang_China_REEC_Seattle_USA'),
        ('later_major_approval_statement','current_major_approval_statement','issuer_assertion_major_scope','not_independent_full_permit_audit')]:
        r=by.loc['donald_'+var]
        routes.append(dict(gate=gate,source_statement=status,limitation=restriction,source_claim_id=r.claim_id,source_id=r.source_id,source_sha256=r.source_sha256,
                           info_public_date=r.info_public_date,locator=r.locator,quote=r.quote,empirical_route_capacity=None,
                           gate_independently_verified=False,commercial_network_ready=False))
    pd.DataFrame(routes).to_csv(OUT/'route_readiness.csv',index=False)
    # Normalize feed to exercise the process envelope; never admit reserve tonnes
    # or nameplate as available stock. All these solves stay under diagnostics.
    solves=[]
    for feed in [0.,0.5,1.,1000.]:
        for label,plant,route,removed in [('finite_feed',feed*2,True,False),('half_throughput',feed/2,True,False),('route_closed',feed*2,False,False),('owner_outage',feed*2,True,True)]:
            solves.append(dict(case=label,**partial_recovery_lp(coefficients,feed,plant,route_open=route,supplier_removed=removed)))
    (DIAG/'donald_partial_lp.json').write_text(json.dumps(solves,indent=2)+'\n')
    pd.DataFrame(checks).to_csv(OUT/'source_numerical_checks.csv',index=False)
    # Figure describes disclosed conditional composition, never forecast supply.
    figure=ROOT/'outputs/conditional/donald';figure.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(10,3.7))
    axes[0].bar(list(OXIDES),[r['recovered_element_t_per_ore_t']*1000 for r in coefficients],color='#a06e32')
    axes[0].set(title='Reserve / pit-design necessary coefficients',ylabel='kg contained element / dry bulk-ore tonne')
    axes[1].bar(list(OXIDES),[r['conditional_element_t_per_reec_t']*1000 for r in comp],color='#587981')
    axes[1].set(title='Financial-model conditional REEC composition',ylabel='kg contained element / as-stated REEC tonne')
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Donald: different disclosed model bases; no operating yield or supply forecast',fontsize=11)
    fig.text(.5,-.04,'Not one linked batch: reserve-average ore and financial REEC assumptions. REEC moisture basis uncertified. No delivered magnets.',ha='center',fontsize=8)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(figure/f'material_bases.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    lines=[r'\begin{tabular}{lrrr}\toprule',r'Element & Oxide (\% HM) & Recovery (\%) & Element (kg/t ore) \\\midrule']
    for r in coefficients:lines.append(f"{r['element']} & {100*r['oxide_fraction_of_HM']:.4g} & {100*r['assumed_recovery']:.0f} & {1000*r['recovered_element_t_per_ore_t']:.4g}"+r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    (ROOT/'manuscript/donald_materials_table.tex').write_text('\n'.join(lines)+'\n')
    result=dict(passed=all(r['passed'] for r in checks+solves+target_checks),freeze='2026-10-11',source_claims=len(selected),
                nested_element_coefficients=len(coefficients),conditional_reec_compositions=len(comp),numerical_checks=len(checks),
                finite_feed_LP_checks=len(solves),vintage_checks=len(target_checks),route_readiness_records=len(routes),cross_report_comparisons=len(compare),
                missed_initial_FID_target_lower_bound_days=lower_bound,reported_interest_2025_percent=9.48,reported_interest_2026H1_percent=current_ef,
                actual_FID_date_identified=False,first_exit_risk_spell_identified=False,empirical_inventory_identified=False,
                operating_recovery_estimated=False,empirical_service_identified=False,forecast_probabilities_produced=False,
                source_bytes_at_freeze_certified=False,independent_engineering_review=False)
    (DIAG/'donald_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Donald source/material/LP/vintage checks failed')


if __name__=='__main__':main()
