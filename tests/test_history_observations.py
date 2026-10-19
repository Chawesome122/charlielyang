"""Historical revisions, missing surveillance and information-leakage guards."""
import pandas as pd
import pytest

from weaponized.rare_earths.history import discovery_roster, disclosure_inventory, milestone_vintages, state_pair_audit


def observation(identifier, public, lo, hi, kind="reported_completion"):
    return dict(record_id=identifier, milestone_id="completion", info_public_date=public,
                event_date_lower=lo, event_date_upper=hi, kind=kind)


def test_later_disjoint_completion_claim_does_not_rewrite_earlier_vintage():
    frame = pd.DataFrame([observation("old", "2025-03-21", "2024-01-01", "2024-12-31"),
                          observation("new", "2026-03-12", "2025-01-01", "2025-12-31")])
    early, audit = milestone_vintages(frame, "2025-12-31")
    assert list(early.record_id) == ["old"]
    assert not audit.reported_timing_conflict.any()
    late, audit = milestone_vintages(frame)
    assert len(late) == 2 and audit.reported_timing_conflict.all()
    assert not audit.actual_event_date_identified.any()


def test_changed_targets_are_not_historical_completion_conflicts():
    frame = pd.DataFrame([observation("a", "2024-03-20", "2024-01-01", "2024-12-31", "target"),
                          observation("b", "2025-03-21", "2025-01-01", "2025-12-31", "target")])
    _, audit = milestone_vintages(frame)
    assert audit.target_window_changed.all()
    assert not audit.reported_timing_conflict.any()


@pytest.mark.parametrize("lo,hi", [("2025-02-30", "2025-03-01"), ("2025-02-02", "2025-02-01"), ("2025-02-01", ""), ("2027-01-01", "2027-02-01"), ("20250201", "2025-03-01"), ("2025-2-1", "2025-03-01")])
def test_malformed_or_future_realized_windows_rejected(lo, hi):
    with pytest.raises(ValueError):
        milestone_vintages(pd.DataFrame([observation("bad", "2025-03-21", lo, hi)]))


def state(identifier, state, valid, public, lo, hi):
    return dict(record_id=identifier, activity_id="plant", state=state, valid_date=valid,
                info_public_date=public, event_date_lower=lo, event_date_upper=hi)


def test_discovery_uses_earliest_visible_source_not_row_order_or_retrospective_event():
    frame = pd.DataFrame([state("later", "S", "2016-01-01", "2026-03-12", "2016-01-01", "2016-12-31"),
                          state("earlier", "F", "2023-07-31", "2024-03-20", "2023-07-31", "2023-07-31"),
                          state("future", "A", "2010-01-01", "2026-10-12", "2010-01-01", "2010-01-01"),
                          state("undated", "A", "2009-01-01", None, None, None)])
    for data in [frame, frame.iloc[::-1]]:
        result = discovery_roster(data).iloc[0]
        assert result.record_id == "earlier"
        assert result.archive_first_documented_public_date == "2024-03-20"
    frame.loc[frame.record_id.eq("undated"), "activity_id"] = "undated_candidate"
    roster = discovery_roster(frame).set_index("activity_id")
    assert pd.isna(roster.loc["undated_candidate", "archive_first_documented_public_date"])


def test_endpoint_pair_classification_does_not_infer_unobserved_first_exit():
    frame = pd.DataFrame([state("a", "A", "2023-01-01", "2023-02-01", "2023-01-01", "2023-01-01"),
                          state("b", "Q", "2024-11-30", "2025-03-21", "2024-11-01", "2024-11-30"),
                          state("c", "Q", "2024-11-30", "2026-03-12", "2024-11-01", "2024-11-30")])
    pairs = state_pair_audit(frame)
    assert list(pairs.pair_class) == ["unobserved_intermediate_states_or_definition_change", "same_state_reobservation"]
    assert pairs.iloc[1].overlapping_or_revised_windows
    assert len(state_pair_audit(frame, "2025-12-31")) == 1


def test_no_news_is_not_survival_and_partial_freeze_quarter_is_explicit():
    frame = pd.DataFrame([state("late", "Q", "2024-11-30", "2025-03-21", "2024-11-01", "2024-11-30"),
                          state("future", "O", "2026-01-01", "2026-10-12", "2026-01-01", "2026-01-01"),
                          state("undated", "A", "2023-01-01", None, None, None)])
    panel = disclosure_inventory(frame, start="2024Q4")
    assert panel.iloc[0].visible_records == 0
    q = panel.set_index("quarter").loc["2025Q1"]
    assert q.visible_records == 1 and q.retrospective_records_disclosed == 1
    assert panel.iloc[-1].origin_date == "2026-10-11" and not panel.iloc[-1].quarter_complete
    assert panel.physical_projects_at_risk.isna().all()
    assert panel.known_survival_exposure_quarters.isna().all()
