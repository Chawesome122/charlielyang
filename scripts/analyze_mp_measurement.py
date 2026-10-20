"""Descriptive producer comparisons, vintage-safe naive hindcasts and figures."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from weaponized.rare_earths.producer_measurement import asof_native, producer_hindcasts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/empirical/rare_earths"


def main():
    data=pd.read_csv(ROOT/"data/processed/mp_measurement/native_cell_versions.csv")
    book=json.loads((ROOT/"codebooks/mp_measurement.json").read_text())
    predictions,audit=producer_hindcasts(data,book["backtest_origins"],book["freeze"])
    if predictions.empty or not (predictions.max_training_public_date.le(predictions.origin) &
                                  predictions.max_training_period_end.le(predictions.origin) &
                                  predictions.target.gt(predictions.origin) & predictions.outcome_public_date.le(book["freeze"])).all():
        raise ValueError("Empty or historically invalid MP native KPI hindcast")
    predictions.to_csv(OUT/"mp_quarterly_baseline_predictions.csv",index=False)
    audit.to_csv(OUT/"mp_quarterly_origin_audit.csv",index=False)
    scores=[]
    for (variable,method),part in predictions.groupby(["variable","method"]):
        scores.append(dict(variable=variable,method=method,n_origins=int(part.origin.nunique()),
                           mae=float(part.error.abs().mean()),rmse=float(np.sqrt((part.error**2).mean()))))
    pd.DataFrame(scores).to_csv(OUT/"mp_quarterly_baseline_scores.csv",index=False)
    lines=[r"\begin{tabular}{lrrrr}\toprule",r"KPI & Origins & Persistence & Seasonal & History mean \\\midrule"]
    score_frame=pd.DataFrame(scores)
    for variable,label in [("REO_production","REO production"),("REO_sales","REO sales"),("NdPr_production","NdPr production"),("NdPr_sales","NdPr sales")]:
        part=score_frame[score_frame.variable.eq(variable)].set_index("method")
        lines.append(f"{label} & {int(part.iloc[0].n_origins)} & {part.loc['latest_available_persistence','mae']:.2f} & {part.loc['seasonal_previous_year','mae']:.2f} & {part.loc['available_history_mean','mae']:.2f}"+r" \\")
    lines.append(r"\bottomrule\end{tabular}")
    (ROOT/"manuscript/mp_baselines.tex").write_text("\n".join(lines)+"\n")
    annual=asof_native(data,book["freeze"])
    fig,axes=plt.subplots(1,2,figsize=(10,3.8))
    for ax,family,title in zip(axes,["REO","NdPr"],["REO content in concentrate","Separated NdPr / oxide-equivalent sales"]):
        for suffix,style in [("production","o-"),("sales","s--")]:
            part=annual[annual.variable.eq(family+"_"+suffix) & annual.cell_status.eq("reported_number")].sort_values("period_end")
            ax.plot(pd.to_datetime(part.period_end).dt.year,part.value,style,label=suffix.capitalize())
        ax.set(title=title,xlabel="Calendar year",ylabel="Native KPI metric tonnes per year")
        ax.set_xticks(sorted(pd.to_datetime(annual[annual.variable.str.startswith(family+"_") & annual.cell_status.eq("reported_number")].period_end).dt.year.unique()))
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle("MP Materials: reported production and sales are distinct measures")
    fig.text(.5,-.02,"Panels cannot be summed. NdPr sales include intercompany transfers from Q4 2025; KPI gaps do not identify inventory.",ha="center",fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:fig.savefig(OUT/f"mp_native_production_sales.{ext}",dpi=220,bbox_inches="tight")
    plt.close(fig)
    quarterly=asof_native(data,book["freeze"],"quarterly")
    fig,axes=plt.subplots(1,2,figsize=(10,3.8))
    for ax,variable,title in zip(axes,["REO_production","NdPr_production"],["Upstream REO content","Finished and packaged NdPr oxide"]):
        part=quarterly[quarterly.variable.eq(variable) & quarterly.cell_status.eq("reported_number")].sort_values("period_end")
        ax.plot(pd.to_datetime(part.period_end),part.value,"o-",color="#236a8a")
        ax.set(title=title,ylabel="Native production KPI tonnes per quarter")
        ax.tick_params(axis="x",rotation=30);ax.grid(alpha=.2)
    fig.suptitle("Reported quarterly production: latest archived comparative cells by freeze")
    fig.text(.5,-.02,"Annual reports publish historical comparisons later. Missing/N/A cells are not zero; no quarterly 2025 table is supplied here.",ha="center",fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:fig.savefig(OUT/f"mp_native_quarterly_production.{ext}",dpi=220,bbox_inches="tight")
    plt.close(fig)
    result=dict(passed=True,evidence_class="empirical_descriptive_hindcast",candidate_origin_metric_pairs=len(audit),
                eligible_origin_metric_pairs=int(audit.status.eq("eligible_common_support").sum()),forecast_records=len(predictions),
                scores=scores,information_set="three archived annual filings; not all contemporary public information",
                actual_vintage="latest archived comparative by freeze; not first-release accuracy",
                statistical_skill_established=False,chemical_recovery_estimated=False,causal_effect_identified=False,
                system_service_forecast=False,overlapping_stages_not_summed=True)
    (OUT/"mp_measurement_analysis.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":main()
