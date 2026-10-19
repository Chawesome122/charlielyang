"""Extract issuer history versions; audit reporting rather than invent risk spells."""
import json
import os
from pathlib import Path
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.rare_earths.history import milestone_vintages

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    specs = json.loads((ROOT/"codebooks/project_history_observations.json").read_text())
    versions, states, checked = [], [], set()
    for spec in specs["observations"]:
        sid = spec["source_id"]
        source = sources[sid]
        if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
            raise ValueError(f"History archive checksum mismatch: {sid}")
        public = source.get("publication_date")
        if not public or public > specs["freeze"]:
            raise ValueError("Missing or post-freeze history source clock")
        text = " ".join((ROOT/f"data/interim/{sid}.txt").read_text().split())
        match = re.search(spec["pattern"], text, re.I)
        if not match:
            raise ValueError(f"Original history quote absent: {spec['record_id']}")
        item = spec | dict(source_sha256=source["sha256"], info_public_date=public,
                           quote=match[0], evidence_class="empirical_issuer_reported",
                           window_basis=specs["window_rule"],
                           valid_date=spec["event_date_upper"] or public)
        versions.append(item)
        checked.add(sid)
        if spec["include_in_state_roster"]:
            states.append(dict(record_id=spec["record_id"], project_id=spec["project_id"],
                               activity_id=spec["activity_id"], site_country="USA",
                               owner_parent="Rare Element Resources / General Atomics; rights not independently adjudicated",
                               control_group_uncertainty="full control/minority rights not independently adjudicated",
                               stage="mine" if spec["activity_id"].endswith("feed") else "separation",
                               state=spec["state"], state_evidence=spec["interpretation"],
                               event_date_lower=spec["event_date_lower"], event_date_upper=spec["event_date_upper"],
                               exact_event_date=spec["event_date_lower"] if spec["event_date_lower"] == spec["event_date_upper"] else None,
                               valid_date=item["valid_date"], info_public_date=public,
                               date_precision="native interval; not automatically state-entry time" if spec["event_date_upper"] else "source-snapshot; event/entry time unknown",
                               first_public_date_verified=False, publication_basis="conservative archived SEC filing date",
                               capacity_native=None, native_unit=None,
                               product_form="Bear Lodge mineral feed" if spec["activity_id"].endswith("feed") else "demonstration separated oxide; not commercial rate",
                               feedstock_origin="Bear Lodge sample; full composition/inventory/recoveries unmeasured",
                               financing="grant/continuation is not proof of fully financed commercial operation",
                               routes="unmeasured", process_yield="unmeasured", utilization="unmeasured",
                               source_id=sid, source_sha256=source["sha256"], locator=spec["locator"], quote=match[0],
                               eligible_for_asof=True, commercial_network_ready=False,
                               cancelled_projects_coverage="selected issuer histories, not complete population",
                               observation_kind=spec["kind"], state_entry_event_verified=False))
    frame, revisions = milestone_vintages(pd.DataFrame(versions), specs["freeze"])
    out = ROOT/"data/processed/project_histories"
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out/"milestone_versions.csv", index=False)
    pd.DataFrame(states).to_csv(out/"state_observations.csv", index=False)
    revisions.to_csv(out/"milestone_revision_audit.csv", index=False)
    latest = frame.sort_values(["info_public_date", "record_id"]).drop_duplicates("milestone_id", keep="last")
    latest = latest.merge(revisions[["milestone_id", "reported_timing_conflict", "target_window_changed"]], on="milestone_id", validate="one_to_one")
    latest.to_csv(out/"latest_visible_milestones.csv", index=False)
    display = frame[frame.record_id.isin(["RH-008", "RH-006", "RH-009", "RH-004", "RH-007", "RH-010"])]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    labels = []
    for i, row in enumerate(display.itertuples()):
        lo, hi = mdates.date2num(pd.to_datetime([row.event_date_lower, row.event_date_upper]))
        color = "#8b5ca6" if row.kind == "target" else "#236a8a"
        ax.barh(i, hi-lo, left=lo, height=.42, color=color, alpha=.7)
        ax.scatter(mdates.date2num(pd.Timestamp(row.info_public_date)), i, color="black", marker="D", s=20)
        labels.append(f"{row.milestone_id.removeprefix('Upton_').replace('_', ' ')}: {row.native_date_phrase}")
    ax.set_yticks(range(len(display)), labels, fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set(title="Upton demonstration: reported milestone vintages", xlabel="Event-window enclosure (bar); verified source availability (black diamond)")
    ax.invert_yaxis()
    fig.text(.5, -.025, "Purple: targets; blue: reported historical claims. Coarse outer windows are not confidence intervals.\nDisjoint completion years remain unadjudicated; demonstration operation is not stable commercial output.", ha="center", fontsize=8)
    fig.tight_layout()
    for extension in ["pdf", "png"]:
        fig.savefig(ROOT/f"outputs/empirical/rare_earths/upton_milestone_vintages.{extension}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    result = dict(passed=True, milestone_versions=len(frame), state_observations=len(states), sources_checked=len(checked),
                  disjoint_reported_milestones=int(revisions.reported_timing_conflict.sum()),
                  changed_target_milestones=int(revisions.target_window_changed.sum()),
                  physical_completion_date_adjudicated=False, population_hazard_identified=False,
                  campaign_metric_target_tonnes=9.1, campaign_basis="issuer's rounded paired total target; not achieved output or annual capacity")
    (ROOT/"outputs/diagnostics/project_history_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
