"""Execute source-version, engineering-basis and issuer accounting comparisons."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from weaponized.io.supplied_evidence import asof_supplied
from weaponized.rare_earths.materials import oxide_element_fraction
from weaponized.semiconductors.operations import wafer_revenue_bridge, revenue_decomposition

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/processed/supplied_evidence"
OUT=ROOT/"outputs/empirical/supplied_evidence"


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    claims=pd.read_csv(DATA/"claims.csv").fillna("")
    smic=pd.read_csv(DATA/"smic_quarterly_versions.csv")
    value=claims.set_index("variable").value
    checks=[]
    for year in [2025,2026]:
        original=float(value[f"mp_cash_ppe_{year}H1"])*1000
        old=pd.read_csv(ROOT/"outputs/empirical/rare_earths/mp_halfyear_cash_ppe.csv")
        fact=float(old[old.year.eq(year)].iloc[0].value)
        checks.append(dict(check=f"MP_{year}_H1_printed_cash_vs_SEC_facts",lhs=original,rhs=fact,passed=original==fact,
                           interpretation="printed cash-flow line agrees; original XBRL tag/context not re-extracted"))
    capacity=[]
    for element in ["ndpr","tb","dy"]:
        first=float(value[f"wm_table_{element}_phase1"]);second=float(value[f"wm_table_{element}_phase2"]);total=float(value[f"wm_table_{element}_total"])
        checks.append(dict(check="White_Mesa_table_component_sum_"+element,lhs=first+second,rhs=total,passed=first+second==total,
                           interpretation="within-table design identity, not achieved output"))
        capacity.append(dict(element=element,table_phase1=first,table_phase2=second,table_total=total,
                             prose_phase1_heavies=None if element=="ndpr" else float(value[f"wm_heavies_prose_{element}"]),
                             native_unit="reported_tpa",observed_output=False,add_to_older_vintage=False,
                             disagreement_requires_adjudication=element!="ndpr"))
    pd.DataFrame(capacity).to_csv(OUT/"white_mesa_design_versions.csv",index=False)
    # Conditional oxide composition in one unit of total rare-earth oxides. No
    # feed availability, raw-monazite TREO grade or operating recovery supplied.
    composition=[]
    for element,formula in [("Nd","Nd2O3"),("Pr","Pr6O11"),("Dy","Dy2O3"),("Tb","Tb4O7")]:
        fraction=float(value["vara_oxide_distribution_"+element.lower()])/100
        composition.append(dict(element=element,oxide=formula,reported_oxide_share_of_TREO=fraction,
                                element_mass_fraction_of_pure_oxide=oxide_element_fraction(formula,element),
                                conditional_element_tonnes_per_tonne_TREO=fraction*oxide_element_fraction(formula,element),
                                classification="reported_assay_distribution_plus_stoichiometry_not_operating_output",
                                raw_monazite_mass_basis_identified=False,operating_recovery_identified=False,
                                annual_feed_available=None,delivered_magnet_service=None,
                                claim_id="SUP:vara_oxide_distribution_"+element.lower()))
    pd.DataFrame(composition).to_csv(OUT/"vara_conditional_oxide_composition.csv",index=False)
    # Only compare cells from the same release: no silent source-vintage splice.
    ratios=[];decompositions=[]
    for (sid,end),part in smic.groupby(["source_id","period_end"]):
        v=part.set_index("variable").value
        for variables,label in [(["wafer_service_revenue_share","other_service_revenue_share"],"service_share"),
                                (["wafer_8inch_revenue_share","wafer_12inch_revenue_share"],"wafer_revenue_size_share")]:
            total=float(v[variables].sum())
            checks.append(dict(check=f"{sid}:{end}:{label}",lhs=total,rhs=100,passed=abs(total-100)<1e-10,
                               interpretation="reported revenue-share denominator, not physical output share"))
        bridge=wafer_revenue_bridge(float(v.total_revenue)*1000,float(v.wafer_service_revenue_share),float(v.wafer_shipments))
        ratios.append(dict(source_id=sid,period_end=end,info_public_date=part.iloc[0].info_public_date,
                           shipments=float(v.wafer_shipments),**bridge))
    frame=pd.DataFrame(ratios)
    frame.to_csv(OUT/"smic_revenue_ratios.csv",index=False)
    for sid,part in frame.groupby("source_id"):
        part=part.sort_values("period_end");current=part.iloc[-1].to_dict()
        for comparison,previous in [("QoQ",part.iloc[-2].to_dict()),("YoY",part.iloc[0].to_dict())]:
            result=revenue_decomposition(current,previous)
            row=dict(source_id=sid,period_end=current['period_end'],comparison=comparison,comparison_period_end=previous['period_end'],
                     shipments_change_pct=100*(current['shipments']/previous['shipments']-1),
                     wafer_revenue_change_pct=100*(current['wafer_attributed_revenue_usd']/previous['wafer_attributed_revenue_usd']-1),
                     nominal_revenue_per_equivalent_change_pct=100*(current['nominal_wafer_revenue_per_reported_equivalent_shipment']/previous['nominal_wafer_revenue_per_reported_equivalent_shipment']-1),**result)
            decompositions.append(row)
            checks.append(dict(check=f'{sid}:{comparison}:revenue_log_identity',lhs=result['identity_residual'],rhs=0,
                               passed=result['passed'],interpretation='nominal accounting identity, not a technology or policy effect'))
    pd.DataFrame(decompositions).to_csv(OUT/"smic_accounting_decompositions.csv",index=False)
    # Keep versions from existing and supplied releases side by side.
    old=pd.read_csv(ROOT/"data/processed/smic_operations/observations.csv")
    allcells=pd.concat([old,smic],ignore_index=True)
    revisions=[]
    for (var,end),part in allcells[allcells.period_frequency.fillna('quarter').eq('quarter')].groupby(['variable','period_end']):
        if len(part)<2:continue
        part=part.sort_values(['info_public_date','source_id'])
        revisions.append(dict(variable=var,period_end=end,versions=len(part),earliest_source=part.iloc[0].source_id,latest_source=part.iloc[-1].source_id,
                              numerical_values_agree=part.value.nunique()==1,product_basis_agrees=part.product_basis.nunique()==1,
                              interpretation='source-comparative audit; definition disagreement does not authorize conversion'))
    pd.DataFrame(revisions).to_csv(DATA/"smic_comparative_versions.csv",index=False)
    pd.DataFrame(checks).to_csv(OUT/"numerical_checks.csv",index=False)
    origins=['2025-12-31','2026-02-25','2026-02-26','2026-05-13','2026-05-14','2026-08-03','2026-08-04','2026-08-05','2026-08-06','2026-08-07','2026-08-09','2026-08-10','2026-08-12','2026-08-13','2026-10-11']
    vintages=[]
    for origin in origins:
        for label,data in [('documentary_claims',claims),('SMIC_native_cells',smic)]:
            selected=asof_supplied(data,origin)
            vintages.append(dict(origin=origin,table=label,admitted_records=len(selected),passed=bool(selected.info_public_date.le(origin).all()),
                                  original_at_vintage_byte_certification=False))
    pd.DataFrame(vintages).to_csv(DATA/"publication_origin_checks.csv",index=False)
    windows=claims[claims.variable.isin(['rer_demo_start','rer_full_processing_target','usar_wheat_ridge_start','usar_swarf_samples','usar_blacksburg_plan','usar_tmrc_closed','mp_ratio_adoption'])]
    windows.to_csv(DATA/"event_definition_windows.csv",index=False)
    # Native quarterly output is not added to concentrate or finished magnets.
    mp=[(2025,float(value['mp_ndpr_production_2025Q2'])),(2026,float(value['mp_ndpr_production_2026Q2']))]
    fig,axes=plt.subplots(1,3,figsize=(10.4,3.5))
    axes[0].bar([str(y)+' Q2' for y,_ in mp],[v for _,v in mp],color=['#9bafb7','#236a8a'])
    axes[0].set(title='MP: packaged NdPr oxide',ylabel='Reported metric tonnes / quarter')
    current=smic[smic.period_end.eq(smic.report_period_end)]
    for ax,var,title,divisor,ylabel in [(axes[1],'wafer_shipments','SMIC: shipments',1e6,'Million standard-logic 8-inch equivalents'),(axes[2],'capacity_utilization','SMIC: utilization',1,'Reported percent')]:
        p=current[current.variable.eq(var)].sort_values('period_end')
        ax.bar([str(pd.Period(d,freq='Q')) for d in p.period_end],p.value/divisor,color='#236a8a');ax.set(title=title,ylabel=ylabel)
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.suptitle('New pre-freeze issuer observations from supplied document copies',fontsize=11)
    fig.text(.5,-.05,'Empirical issuer reporting; separate sectors and product bases. No end-to-end magnet service, target semiconductor capability or causal effect.',ha='center',fontsize=8)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(OUT/f'quarterly_observations.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    lines=[r'\begin{tabular}{lrrr}\toprule',r'SMIC comparison & Shipments & Wafer revenue & Revenue/equivalent \\\midrule']
    for r in decompositions:
        label=str(pd.Period(r['period_end'],freq='Q'))+' '+r['comparison']
        lines.append(f"{label} & {r['shipments_change_pct']:.1f} & {r['wafer_revenue_change_pct']:.1f} & {r['nominal_revenue_per_equivalent_change_pct']:.1f}"+r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    (ROOT/'manuscript/supplied_smic_changes.tex').write_text('\n'.join(lines)+'\n')
    result=dict(passed=all(r['passed'] for r in checks+vintages),numerical_checks=len(checks),vintage_checks=len(vintages),
                smic_accounting_decompositions=len(decompositions),smic_comparative_groups=len(revisions),
                smic_comparative_numeric_disagreements=sum(not r['numerical_values_agree'] for r in revisions),
                wm_prose_table_disagreements=2,conditional_element_compositions=len(composition),
                mp_q2_2026_ndpr_oxide_tonnes=840,mp_h1_2026_ndpr_oxide_tonnes=1757,
                mp_sales_ratio_adoption='2026Q1',mp_prior_periods_recast=False,
                rer_formal_demo_start='2026-03',rer_end_to_end_target='2026Q3',rer_target_observed_by_this_source=False,
                empirical_service_identified=False,causal_effect_estimated=False,forecast_probabilities_produced=False,
                source_bytes_at_freeze_certified=False)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Source-derived numerical or vintage check failed')


if __name__=='__main__':main()
