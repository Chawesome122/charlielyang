"""Plot native disclosures without converting intermediate forms or stocks."""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def save(fig, name):
    out = ROOT/"outputs/empirical/rare_earths"
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for extension in ["pdf", "png"]:
        fig.savefig(out/f"{name}.{extension}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    ratios = pd.read_csv(ROOT/"data/processed/white_mesa/reported_flow_ratios.csv")
    yearly = ratios[ratios.episode_id.isin(["WhiteMesa_2022_reported_processing", "WhiteMesa_2023_reported_processing"])].copy()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.7))
    x = np.arange(len(yearly))
    axes[0].bar(x-.18, yearly.feed, width=.36, label="Bulk monazite processed", color="#236a8a")
    axes[0].bar(x+.18, yearly.output, width=.36, label="Contained TREO in RE carbonate", color="#ba8a4c")
    axes[0].set(xticks=x, xticklabels=["2022", "2023"], ylabel="Reported metric tonnes; distinct mass bases", title="Native annual input/output disclosures")
    axes[0].legend(fontsize=7, loc="upper left")
    episode = ratios[ratios.episode_id.eq("WhiteMesa_2024_commissioning_run")].sort_values("info_public_date")
    axes[1].bar(["FY2024 source:\nNdPr oxalate", "FY2025 source:\nNdPr oxide"], episode.output, color=["#8a669e", "#236a8a"])
    axes[1].set(ylabel="Reported product tonnes; form unadjudicated", title="One 2024 run, two source descriptions", ylim=(0,48))
    fig.text(.5, -.07, "Actual issuer disclosures, not chemical recoveries or independent batches. 2021 generic tons are not converted.\nCarbonate-contained TREO, oxalate and oxide are not interchangeable; no inventory balance or magnet service is inferred.", ha="center", fontsize=8)
    save(fig, "white_mesa_native_flows")
    data = pd.read_csv(ROOT/"data/processed/white_mesa/observations.csv")
    data = data[data.quantity_role.eq("expected_capacity_table")]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.4))
    for ax, product in zip(axes, ["NdPr_table_native_product", "TB", "DY"]):
        part = data[data.product_basis.eq(product)]
        values = dict(zip(part.component, pd.to_numeric(part.value)))
        ax.bar(["Components"], [values["p1"]], color="#236a8a", label="Phase 1 table component")
        ax.bar(["Components"], [values["p2"]], bottom=[values["p1"]], color="#ba8a4c", label="Planned Phase 2")
        ax.axhline(values["total"], color="#444444", linestyle="--", linewidth=1)
        ax.set(title={"NdPr_table_native_product":"NdPr", "TB":"Tb", "DY":"Dy"}[product], ylabel="Native expected table tpa", ylim=(0,values["total"]*1.18))
        ax.text(0, values["total"]*1.035, f"Combined: {values['total']:,.0f}", ha="center", fontsize=8)
    axes[0].legend(fontsize=7, loc="upper left", bbox_to_anchor=(-.05,-.12))
    fig.text(.5, -.15, "Conditional issuer capacity table, not observed throughput. Phase 1 HREE additions are planned;\nits existing NdPr label does not verify the expected rate. Combined totals are not added again; product panels are not summed.", ha="center", fontsize=8)
    save(fig, "white_mesa_capacity_components")


if __name__ == "__main__":
    main()
