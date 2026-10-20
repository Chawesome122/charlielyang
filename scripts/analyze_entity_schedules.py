"""Descriptive issued-entry counts and documentary clocks, never access effects."""
from datetime import datetime
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    frame = pd.read_csv(ROOT/"data/processed/entity_schedules/entries.csv", keep_default_na=False)
    clocks = pd.read_csv(ROOT/"data/processed/entity_schedules/source_clocks.csv")
    out = ROOT/"outputs/empirical/semiconductors"
    out.mkdir(parents=True, exist_ok=True)
    frame["destination_group"] = np.where(frame.destination.eq("CHINA, PEOPLE'S REPUBLIC OF"), "China printed heading", "Other printed headings")
    categories = ["presumption_of_denial", "policy_of_denial", "mixed_denial_and_case_by_case", "case_by_case", "cross_referenced_review_unresolved"]
    documents = sorted(frame.document_number.unique())
    counts = frame.groupby(["document_number", "destination_group", "review_category"]).size().rename("printed_entry_versions").reset_index()
    counts.to_csv(out/"entity_review_counts.csv", index=False)
    quality = []
    for row in frame.to_dict("records"):
        display = datetime.strptime(row["publication_date"], "%Y-%m-%d").strftime("%B %-d, %Y")
        quality.append(dict(entry_id=row["entry_id"], document_number=row["document_number"],
                            source_sha256=row["source_sha256"], start_xpath=row["start_xpath"],
                            citation_insert_placeholder="INSERT" in row["citation_cell_text"],
                            rule_date_token_in_entity_text=display in row["entity_text"],
                            referenced_note_not_reprinted=bool(json.loads(row["unprinted_footnote_refs"])),
                            entry_action_unresolved=row["action_adjudication"] not in {"addition","revision"},
                            instruction_name_discrepancy=row["name_variant_requires_expert_review"],
                            source_text_preserved=True, correction_adjudicated=False))
    quality = pd.DataFrame(quality)
    quality.to_csv(out/"entity_source_quality_flags.csv", index=False)
    colors = ["#236a8a", "#c06427", "#669a66", "#9472a6", "#888888"]
    labels = ["Presumption of denial", "Policy of denial", "Mixed denial / case-by-case", "Case-by-case", "Cross-reference unresolved"]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2), sharey=True)
    for ax, group in zip(axes, ["China printed heading", "Other printed headings"]):
        matrix = pd.crosstab(frame.loc[frame.destination_group.eq(group), "document_number"], frame.loc[frame.destination_group.eq(group), "review_category"]).reindex(index=documents, columns=categories, fill_value=0)
        bottom = np.zeros(len(documents))
        for category, label, color in zip(categories, labels, colors):
            y = matrix[category].to_numpy()
            ax.bar(np.arange(len(documents)), y, bottom=bottom, color=color, label=label)
            bottom += y
        ax.set(title=group, xticks=np.arange(len(documents)), xticklabels=documents)
        ax.tick_params(axis="x", rotation=65, labelsize=8)
        ax.grid(axis="y", alpha=.2)
    axes[0].set_ylim(0, 1.15*frame.groupby(["document_number","destination_group"]).size().max())
    axes[0].set_ylabel("Printed destination-specific entry versions")
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(.5, -.055))
    fig.suptitle("Review standards in nine selected issued Entity List schedules", fontsize=11)
    fig.tight_layout(rect=(0,.08,1,1))
    for ext in ["pdf", "png"]:
        fig.savefig(out/f"entity_review_policies.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    clocks = clocks.sort_values("document_number")
    y = np.arange(len(clocks))
    for i, row in enumerate(clocks.to_dict("records")):
        ax.plot([row["filing_minus_effective_days"], row["public_minus_effective_days"]], [i,i], color="#aaaaaa")
    ax.scatter(clocks.filing_minus_effective_days, y, label="Official reported filing date", color="#236a8a", marker="s")
    ax.scatter(clocks.public_minus_effective_days, y, label="Federal Register publication", color="#c06427")
    ax.axvline(0, color="#444444", linestyle="--", linewidth=.8, label="Rule effective date")
    ax.set(yticks=y, yticklabels=clocks.document_number, xlabel="Calendar days relative to stated effective date", title="Three documentary dates; no observed transaction or access effect")
    ax.invert_yaxis(); ax.grid(axis="x", alpha=.2); ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(out/f"entity_publication_clocks.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    table = frame.groupby("document_number").agg(
        entries=("entry_id", "size"),
        china=("destination_group", lambda s: int(s.eq("China printed heading").sum())),
        mixed=("review_category", lambda s: int(s.eq("mixed_denial_and_case_by_case").sum())),
        cross_reference=("review_category", lambda s: int(s.eq("cross_referenced_review_unresolved").sum())),
    )
    table.to_csv(out/"entity_schedule_summary_table.csv")
    lines = [r"\begin{tabular}{lrrrr}\toprule", r"Issued rule & Entries & China heading & Mixed review & Cross-reference \\\midrule"]
    for doc, row in table.iterrows():
        lines.append(f"{doc} & {row.entries} & {row.china} & {row.mixed} & {row.cross_reference}"+r" \\")
    lines.append(r"\bottomrule\end{tabular}")
    (ROOT/"manuscript/entity_schedules_table.tex").write_text("\n".join(lines)+"\n")
    assert len(quality)==len(frame) and int(table.entries.sum())==len(frame)==int(counts.printed_entry_versions.sum())
    result = dict(passed=True, evidence_class="primary_legal_issued_schedule_descriptive",
                  printed_entry_versions=len(frame), china_heading_entries=int(table.china.sum()),
                  other_heading_entries=int(table.entries.sum()-table.china.sum()),
                  review_categories=frame.review_category.value_counts().to_dict(),
                  source_quality_flags={key:int(quality[key].sum()) for key in ["citation_insert_placeholder","rule_date_token_in_entity_text","referenced_note_not_reprinted","entry_action_unresolved","instruction_name_discrepancy"]},
                  entry_actions=frame.action_adjudication.value_counts().to_dict(),
                  rules_with_filing_before_effective=int(clocks.filing_minus_effective_days.lt(0).sum()),
                  rules_with_publication_after_effective=int(clocks.public_minus_effective_days.gt(0).sum()),
                  publication_only_omissions_at_effective_date=int(pd.read_csv(ROOT/"data/processed/entity_schedules/publication_vintage_checks.csv").publication_only_omits_at_effective_date.sum()),
                  printed_address_entries=int(frame.entry_kind.eq("address_entry").sum()),
                  unique_new_company_count_identified=False, complete_China_or_semiconductor_coverage=False,
                  current_law_consolidated=False, foreign_access_or_causal_effect_identified=False,
                  source_flags_measure_policy_opacity=False,
                  uncertainty="Source transcription/rendering and legal/entity adjudication; no sampling confidence interval or approval probability identified")
    (out/"entity_schedules_analysis.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
