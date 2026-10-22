"""Generate source-checked attrition/coverage tables for the actual roster."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.rare_earths.evidence import documented_activity_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    records = pd.read_csv(ROOT/"data/processed/rare_earths/project_state_evidence.csv")
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").fillna("").to_dict("records"):
        sources[row["source_id"]] = row
    for row in json.loads((ROOT/'metadata/user_supplied_sources.json').read_text()):
        sources[row['source_id']]=row
    checked = set()
    for row in records.to_dict("records"):
        source = sources[row["source_id"]]
        if row["source_sha256"] != source["sha256"]:
            raise ValueError("Project/source hash mismatch")
        if source["source_id"] not in checked:
            if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
                raise ValueError("Project source bytes changed")
            checked.add(source["source_id"])
    flags = documented_activity_snapshot(records)
    cols = ["activity_id", "project_id", "stage", "source_id", "source_sha256", "info_public_date", "state",
            "public_clock_eligible", "native_capacity_documented", "annual_native_capacity_documented",
            "finite_campaign_limit_documented", "capacity_time_basis", "complete_element_recipe_verified",
            "finite_route_capacity_verified", "independent_stable_qualified_rate_verified", "final_grade_demand_matched"]
    flags[cols].to_csv(ROOT/"data/processed/industrial_evidence/activity_coverage.csv", index=False)
    metrics = cols[7:11] + cols[12:]
    grouped = flags.groupby("stage")[metrics].sum().reindex(["mine", "separation", "metal_alloy", "magnet"])
    grouped.insert(0, "documented_activities", flags.groupby("stage").size())
    out = ROOT/"outputs/empirical/rare_earths"
    grouped.to_csv(out/"evidence_coverage_by_stage.csv")
    fig, ax = plt.subplots(figsize=(9, 4))
    grouped[["documented_activities", "public_clock_eligible", "annual_native_capacity_documented"]].plot.bar(ax=ax, rot=0)
    ax.set(title="Documentation coverage in the selected project roster", ylabel="Activities with documented fields", xlabel="Production stage")
    ax.set_xticklabels(["Mining/feed", "Separation", "Metal/alloy", "Magnets"])
    ax.legend(["Discovery activities", "Verified source-public clock", "Native annual capacity mentioned"], fontsize=8)
    fig.text(.5, -.03, "Counts are evidence coverage, not tonnes, operating capacities or population estimates.\nNo complete element recipe, finite route capacity, independent stable qualified rate or matched final demand is verified.", ha="center", fontsize=8)
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(out/f"evidence_coverage.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    result = dict(passed=True, roster_records=len(records), discovery_projects=int(records.project_id.nunique()),
                  discovery_activities=len(flags), source_pdfs_or_filings_checked=len(checked),
                  documentation_counts={key:int(value) for key, value in flags[metrics].sum().items()},
                  scientific_scope="coverage within a selected discovery roster; no population denominator or service estimate",
                  zero_counts_mean="no verified observation in this archive, not no real-world capacity or deliberate opacity")
    (ROOT/"outputs/diagnostics/evidence_coverage_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
