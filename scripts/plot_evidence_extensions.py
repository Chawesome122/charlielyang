"""Plot source-reported model assumptions and actual claim-clock exclusions."""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def save(fig, directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for extension in ["pdf", "png"]:
        fig.savefig(directory/f"{name}.{extension}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    source = pd.read_csv(ROOT/"data/processed/engineering_inputs/observations.csv")
    source = source[source.variable.eq("separation_recovery")]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.5))
    contexts = ["resource_pit_optimization", "reserve_pit_optimization"]
    for ax, product in zip(axes, ["Ce Chloride", "La Carbonate"]):
        for offset, year, color in [(-.18, 2024, "#236a8a"), (.18, 2025, "#ba8a4c")]:
            values = [float(source[source.source_id.eq(f"RE-MP-10K{year}") & source.product_basis.eq(product) & source.engineering_context.eq(context)].iloc[0].value) for context in contexts]
            ax.bar(np.arange(2)+offset, values, width=.36, label=f"FY{year} report", color=color)
        ax.set(xticks=[0, 1], xticklabels=["Resource model", "Reserve model"],
               title=product, ylabel="Reported model recovery assumption (%)")
    axes[1].legend(fontsize=8, loc="lower left")
    fig.suptitle("Mountain Pass: source-vintaged engineering assumptions", fontsize=11)
    fig.text(.5, -.07, "Calibrated issuer pit-model inputs, not measured operating recoveries or production changes.\nProduct forms and resource/reserve contexts remain separate; carbonate/chloride mass is not oxide mass.", ha="center", fontsize=8)
    save(fig, ROOT/"outputs/calibrated/engineering", "recovery_assumption_versions")

    masking = pd.read_csv(ROOT/"data/processed/publication_extension/claim_origin_masking.csv")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    known = masking.event_date_and_public_clock_available.to_numpy()
    leaked = masking.event_date_only_lookahead_claims.to_numpy()
    ax.bar(masking.origin, known, color="#236a8a", label="Event date and source-public clock available")
    ax.bar(masking.origin, leaked, bottom=known, color="#ba8a4c", label="Look-ahead if only event date is used")
    ax.set(ylabel="Claim versions in event-date-only selection", title="Actual 37-claim finance/material dataset: public-clock exclusions")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(fontsize=8, loc="upper left")
    fig.text(.5, -.055, "Historical information-set audit, not forecast performance. Issuer-stated public availability\nis separate from independently certified original-at-vintage bytes, which remain unavailable.", ha="center", fontsize=8)
    save(fig, ROOT/"outputs/empirical/source_integrity", "claim_clock_exclusions")


if __name__ == "__main__":
    main()
