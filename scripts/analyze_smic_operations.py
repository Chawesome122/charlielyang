"""Descriptive scale/revenue accounting; no causal or target-capability estimation."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from weaponized.semiconductors.operations import asof_operations, revenue_decomposition, wafer_revenue_bridge

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/empirical/semiconductors"


def main():
    data=pd.read_csv(ROOT/"data/processed/smic_operations/observations.csv")
    OUT.mkdir(parents=True,exist_ok=True)
    bridges=[]
    for (sid,period),part in data[data.period_frequency.eq("quarter")].groupby(["source_id","period_end"]):
        v=part.set_index("variable").value
        if not {"total_revenue","wafer_service_revenue_share","wafer_shipments"}.issubset(v.index):
            continue
        ship=part[part.variable.eq("wafer_shipments")].iloc[0]
        bridges.append(dict(source_id=sid,source_sha256=ship.source_sha256,info_public_date=ship.info_public_date,
                            period_end=period,shipments=float(v.wafer_shipments),shipment_basis=ship.product_basis,
                            reported_wafer_revenue_share_percent=float(v.wafer_service_revenue_share),
                            **wafer_revenue_bridge(float(v.total_revenue)*1000,float(v.wafer_service_revenue_share),float(v.wafer_shipments))))
    bridge=pd.DataFrame(bridges)
    bridge.to_csv(OUT/"smic_wafer_revenue_ratios.csv",index=False)
    decompositions=[]
    for sid,part in bridge.groupby("source_id"):
        year=int(sid[10:14]);current=part[part.period_end.eq(f"{year}-12-31")].iloc[0].to_dict()
        for label,period in [("QoQ",f"{year}-09-30"),("YoY",f"{year-1}-12-31")]:
            previous=part[part.period_end.eq(period)].iloc[0].to_dict()
            result=revenue_decomposition(current,previous)
            decompositions.append(dict(source_id=sid,info_public_date=current["info_public_date"],
                                        period_end=current["period_end"],comparison=label,comparison_period_end=period,
                                        current_shipment_basis=current["shipment_basis"],comparative_shipment_basis=previous["shipment_basis"],
                                        source_native_shipments_change_pct=100*(current["shipments"]/previous["shipments"]-1),
                                        source_native_wafer_revenue_change_pct=100*(current["wafer_attributed_revenue_usd"]/previous["wafer_attributed_revenue_usd"]-1),
                                        source_native_revenue_per_equivalent_shipment_change_pct=100*(current["nominal_wafer_revenue_per_reported_equivalent_shipment"]/previous["nominal_wafer_revenue_per_reported_equivalent_shipment"]-1),
                                        historical_comparative_conversion_verified=False,**result))
    dec=pd.DataFrame(decompositions)
    dec.to_csv(OUT/"smic_revenue_decompositions.csv",index=False)
    latest=asof_operations(data,"2026-10-11")
    fig,axes=plt.subplots(1,3,figsize=(10.8,3.8))
    for ax,variable,title,divisor,ylabel in zip(axes,
            ["wafer_shipments","monthly_capacity","capacity_utilization"],
            ["Quarterly shipments","Reported monthly capacity","Quarterly utilization"],
            [1e6,1e6,1],
            ["Million reported equivalent wafers","Million equivalents / month","Utilization (%)"]):
        part=latest[latest.variable.eq(variable)].sort_values("period_end")
        groups=[("generic_8inch_equivalent","Generic 8-inch equivalent","#236a8a","o"),
                ("standard_logic_8inch_equivalent","Standard logic equivalent","#c06427","s")]
        if variable=="capacity_utilization":groups=[("wafers_out_over_estimated_quarterly_capacity","Reported utilization","#444444","o")]
        for basis,label,color,marker in groups:
            selected=part[part.product_basis.eq(basis)]
            ax.scatter(pd.to_datetime(selected.period_end),selected.value/divisor,label=label,color=color,marker=marker,s=35)
        ax.set(title=title,ylabel=ylabel);ax.xaxis.set_major_locator(mdates.YearLocator(1,12,31));ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y Q4"));ax.tick_params(axis="x",rotation=30);ax.grid(alpha=.2)
    axes[0].legend(fontsize=8,loc="best")
    fig.suptitle("SMIC reported operating scale: selected source-vintaged quarters",fontsize=11)
    fig.text(.5,-.055,"Colors follow latest archived source wording, including comparatives; no adoption date is inferred.\nSelected quarters only; these aggregates do not establish advanced-target capability or foreign access.",ha="center",fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:fig.savefig(OUT/f"smic_operating_scale.{ext}",dpi=220,bbox_inches="tight")
    plt.close(fig)
    yoy=dec[dec.comparison.eq("YoY")].sort_values("period_end")
    x=np.arange(len(yoy));q=yoy.log_shipments_change.to_numpy()*100;r=yoy.log_revenue_per_equivalent_shipment_change.to_numpy()*100
    fig,ax=plt.subplots(figsize=(8.2,3.9))
    ax.bar(x,q,label="Reported shipments",color="#236a8a")
    ax.bar(x,r,bottom=np.where(q*r>=0,q,0),label="Nominal revenue / reported equivalent shipment",color="#c06427")
    ax.plot(x,yoy.log_wafer_revenue_change*100,"ko",label="Wafer-attributed nominal revenue")
    ax.axhline(0,color="grey",linewidth=.7)
    ax.set(xticks=x,xticklabels=[str(d[:4])+" Q4" for d in yoy.period_end],ylabel="100 × log year-on-year change",title="Source-native wafer revenue: an accounting decomposition")
    ax.legend(fontsize=7);ax.grid(axis="y",alpha=.2)
    fig.text(.5,-.025,"Rounded revenue shares; current-source comparative definitions. The ratio term is not a quality-adjusted price, technology effect or causal policy estimate.",ha="center",fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:fig.savefig(OUT/f"smic_revenue_decomposition.{ext}",dpi=220,bbox_inches="tight")
    plt.close(fig)
    lines=[r"\begin{tabular}{lrrr}\toprule",r"Q4 vs. prior Q4 & Shipments & Wafer revenue & Revenue/equivalent \\\midrule"]
    for row in yoy.to_dict("records"):
        lines.append(f"{row['period_end'][:4]} & {row['source_native_shipments_change_pct']:.1f} & {row['source_native_wafer_revenue_change_pct']:.1f} & {row['source_native_revenue_per_equivalent_shipment_change_pct']:.1f}"+r" \\")
    lines.append(r"\bottomrule\end{tabular}")
    (ROOT/"manuscript/smic_operating_changes.tex").write_text("\n".join(lines)+"\n")
    result=dict(passed=bool(dec.passed.all()),evidence_class="issuer_reported_descriptive_accounting",
                revenue_ratio_records=len(bridge),accounting_decompositions=len(dec),
                max_abs_identity_residual=float(dec.identity_residual.abs().max()),
                quarterly_periods_not_continuous=True,revenue_shares_are_rounded=True,
                quality_adjusted_price_identified=False,advanced_node_or_domestic_tool_capability_identified=False,
                foreign_access_identified=False,causal_effect_identified=False,
                latest_source_YoY_comparison=yoy.iloc[-1].to_dict(),
                limitations=["one firm; selected Q3/Q4 releases", "unaudited issuer operating figures", "unreconstructed equivalent-wafer convention history", "no comparison panel, target yield/node or equipment-origin measurement"])
    (OUT/"smic_operations_analysis.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:raise ValueError("Accounting identity failed")


if __name__ == "__main__":main()
