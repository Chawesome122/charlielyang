"""Observation histories are distinct from continuously observed risk spells."""
from datetime import date

import pandas as pd

from .projects import ALLOWED


def discovery_roster(frame, freeze="2026-10-11"):
    """Earliest documented source clock in this archive, not project birth.

    Insertion order and retrospective event dates must not determine when an
    activity entered the available information set. Undated candidates remain
    explicit; future publications do not enter an earlier discovery universe.
    """
    data = frame.copy()
    dates = pd.to_datetime(data.info_public_date, errors="raise")
    data = data[dates.isna() | dates.le(pd.Timestamp(freeze))].copy()
    data["_archive_public_clock"] = pd.to_datetime(data.info_public_date, errors="raise")
    data = data.sort_values(["_archive_public_clock", "record_id"], na_position="last")
    data = data.drop_duplicates("activity_id", keep="first")
    data["archive_first_documented_public_date"] = data["_archive_public_clock"].dt.strftime("%Y-%m-%d")
    data["archive_discovery_basis"] = "earliest verified source clock in this selected archive; true announcement/state entry not established"
    return data.drop(columns="_archive_public_clock").reset_index(drop=True)


def milestone_vintages(frame, origin="2026-10-11"):
    """Retain visible versions and flag disjoint reported event windows.

    A changed target is not a realized event. Disjoint historical claims may
    reflect rework or changed definitions; neither is silently adjudicated true.
    """
    data = frame.copy().fillna("")
    public = pd.to_datetime(data.info_public_date, errors="raise")
    if (data.info_public_date == "").any():
        raise ValueError("A milestone version requires a source-public clock")
    data = data[public.le(pd.Timestamp(origin))].copy()
    for row in data.to_dict("records"):
        if date.fromisoformat(row["info_public_date"]).isoformat() != row["info_public_date"]:
            raise ValueError("Public clocks require canonical YYYY-MM-DD dates")
        lo, hi = row.get("event_date_lower", ""), row.get("event_date_upper", "")
        if bool(lo) != bool(hi) or (lo and lo > hi):
            raise ValueError("Event windows must be complete and ordered")
        if lo:
            if date.fromisoformat(lo).isoformat() != lo or date.fromisoformat(hi).isoformat() != hi:
                raise ValueError("Event windows require canonical YYYY-MM-DD dates")
        if hi and hi > row["info_public_date"] and row["kind"] != "target":
            raise ValueError("Future targets cannot become observed milestones")
    data = data.sort_values(["info_public_date", "record_id"])
    audits = []
    for milestone, part in data.groupby("milestone_id", sort=True):
        known = part[part.event_date_lower.ne("")]
        actual = known[known.kind.ne("target")]
        intervals = list(zip(actual.event_date_lower, actual.event_date_upper))
        disjoint = any(a[1] < b[0] or b[1] < a[0]
                       for i, a in enumerate(intervals) for b in intervals[i+1:])
        targets = known[known.kind.eq("target")]
        changed = len(set(zip(targets.event_date_lower, targets.event_date_upper))) > 1
        audits.append(dict(milestone_id=milestone, visible_versions=len(part),
                           reported_timing_conflict=disjoint, target_window_changed=changed,
                           latest_record_id=part.iloc[-1].record_id,
                           adjudication="definition/rework/original-source review required" if disjoint else "no disjoint reported windows detected",
                           actual_event_date_identified=False))
    return data.reset_index(drop=True), pd.DataFrame(audits)


def state_pair_audit(frame, origin="2026-10-11"):
    """Diagnose observed milestone pairs without inventing first-exit spells.

    Adjacent endpoints can hide multiple transitions, re-entry and reporting
    delays. Allowed pairs alone do not prove a first exit or known exposure.
    """
    data = frame.copy().fillna("")
    data = data[data.info_public_date.ne("") & data.info_public_date.le(origin)]
    rows = []
    for activity, part in data.groupby("activity_id", sort=True):
        part = part.sort_values(["valid_date", "info_public_date", "record_id"])
        records = part.to_dict("records")
        for first, second in zip(records, records[1:]):
            a, b = first["state"], second["state"]
            missing = any(not r.get(k) for r in [first, second]
                          for k in ["event_date_lower", "event_date_upper"])
            overlap = not missing and first["event_date_upper"] >= second["event_date_lower"]
            kind = "same_state_reobservation" if a == b else "allowed_endpoint_pair" if b in ALLOWED[a] else "unobserved_intermediate_states_or_definition_change"
            rows.append(dict(activity_id=activity, first_record=first["record_id"], second_record=second["record_id"],
                             from_state=a, to_state=b, pair_class=kind,
                             missing_event_window=missing, overlapping_or_revised_windows=overlap,
                             first_exit_likelihood_admissible=False,
                             reason="No complete-surveillance/first-exit protocol or verified state-entry risk spell; selected discovery population"))
    return pd.DataFrame(rows)


def disclosure_inventory(frame, start="2016Q1", freeze="2026-10-11"):
    """Count source-visible records, never interpret no news as survival.

    A partial final quarter ends at the freeze. Event windows alone do not
    establish a physical state throughout the quarters between disclosures.
    """
    data = frame.copy().fillna("")
    dates = pd.to_datetime(data.info_public_date, errors="coerce")
    data = data[dates.notna() & dates.le(pd.Timestamp(freeze))].copy()
    rows = []
    for q in pd.period_range(start, pd.Period(freeze, freq="Q"), freq="Q"):
        end = min(q.end_time.normalize(), pd.Timestamp(freeze))
        begin = q.start_time.date().isoformat()
        origin = end.date().isoformat()
        visible = data[data.info_public_date.le(origin)]
        new = visible[visible.info_public_date.ge(begin)]
        retrospective = new.event_date_upper.ne("") & new.event_date_upper.lt(begin)
        rows.append(dict(quarter=str(q), origin_date=origin, quarter_complete=end == q.end_time.normalize(),
                         visible_records=len(visible), activities_with_source_history=visible.activity_id.nunique(),
                         new_source_records=len(new), retrospective_records_disclosed=int(retrospective.sum()),
                         physical_projects_at_risk=None, known_survival_exposure_quarters=None,
                         representative_cohort_verified=False))
    return pd.DataFrame(rows)
