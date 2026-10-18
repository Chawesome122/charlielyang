#!/usr/bin/env python3
"""Small descriptive quarterly hindcasts using verified publication clocks.

The observed information set is our archived source subset, not a claim to all
public investor information. No trained model, significance claim or physical
magnet-service probability is supplied by these naive native-output forecasts.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from weaponized.rare_earths.reported_output import hindcasts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/empirical/rare_earths"



def main():
    versions = pd.read_csv(ROOT / "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv")
    rows = hindcasts(versions)
    if not (rows.max_training_public_date.le(rows.origin) & rows.max_training_period_end.le(rows.origin) & rows.target.gt(rows.origin)).all():
        raise ValueError("Hindcast information leakage")
    rows["error"] = rows.prediction - rows.actual
    rows.to_csv(OUT / "lynas_quarterly_baseline_predictions.csv", index=False)
    scores = []
    for (product, method), part in rows.groupby(["product_basis", "method"]):
        scores.append(dict(product_basis=product, method=method, n_origins=int(part.origin.nunique()),
                           mae=float(part.error.abs().mean()), rmse=float(np.sqrt((part.error ** 2).mean())),
                           signed_mean_error=float(part.error.mean())))
    pd.DataFrame(scores).to_csv(OUT / "lynas_quarterly_baseline_scores.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, product in zip(axes, ["NdPr_oxide_product_family", "total_REO"]):
        data = rows[rows.product_basis.eq(product)]
        observations = data.drop_duplicates("target").sort_values("target")
        ax.plot(pd.to_datetime(observations.target), observations.actual, "ko-", label="Reported actual")
        for method, part in data.groupby("method"):
            ax.plot(pd.to_datetime(part.target), part.prediction, ".--", label=method.replace("_", " "))
        ax.set(title="NdPr product family" if product.startswith("NdPr") else "Total REO", ylabel="Native reported tonnes per quarter")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=6)
    fig.suptitle("Lynas: descriptive publication-safe quarterly baseline comparisons")
    fig.text(.5, -.025, "One issuer; eight origins per product; archived information subset; no claim of statistical skill or magnet-service resilience.", ha="center", fontsize=8)
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(OUT / f"lynas_quarterly_baselines.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    result = dict(passed=True, evidence_class="empirical_descriptive_hindcast", scores=scores,
                  horizon="next calendar quarter after quarter-end origin; publication lags respected",
                  information_set="archived quarterly front-page tables only; not all contemporary public information",
                  statistical_skill_established=False, causal_effect_identified=False,
                  system_service_forecast=False, limitations=["one issuer", "eight dependent origins", "changing commissioning and operating conditions", "partial historical source universe"])
    (OUT / "lynas_quarterly_baseline_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
