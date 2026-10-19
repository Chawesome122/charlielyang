# Project histories, revisions and observation audit

Information freeze: 2026-10-11. Continuation executed across 2026-10-18–19 UTC. The source records are already archived pre-freeze SEC originals; no inaccessible quarterly filing contributes observations.

## Source findings

`codebooks/project_history_observations.json` registers 15 observations from Rare Element Resources FY2023, FY2024 and FY2025 Forms 10-K, conservatively available on 2024-03-20, 2025-03-21 and 2026-03-12. `scripts/build_project_histories.py` checks original archive hashes, source-public clocks and exact quoted text. Five state observations extend the discovery roster to 60 records, still 24 projects/32 activities. They add history, not new independent projects.

The FY2024 filing reports substantial Upton demonstration-plant construction completion in **late 2024**. FY2025 reports **late 2025**, with commissioning paused for review/rework after its November 2024 start, followed by formal plant operations in early 2026. Both original completion statements survive in the version table. Disjoint reported years require adjudication of event definition, rework and contemporaneous evidence; this is not proof of an erroneous disclosure. The latest visible record is an information version, not a certified true completion date.

The FY2023 report scheduled plant operation in mid-2024; FY2024 expected mid-2025. These are targets, separately coded from realized milestones. Equipment shakedown and finite demonstration operations do not establish commercial throughput, customer qualification or an operating mine. A commissioning pause with unknown dates is not automatically a whole-project suspended-state transition. Partial environmental work at Bear Lodge in 2024 is also distinct from its reported formal permitting restart in early 2026.

The FY2024 report explicitly states a total planned campaign of **10 tons (9.1 tonnes)** of NdPr oxide. Preserve this rounded metric counterpart. It does not identify an exact ton standard, an annual rate, achieved output, elemental recovery, available future inventory or a replenishable input stream. The original FY2025 native-ton campaign record remains unchanged; the new source provides additional measurement evidence.

## Timing and vintage rules

Native “mid” and “late” year phrases use the full calendar year as a conservative outer enclosure. No quarter, exact date, within-window probability distribution or confidence interval is invented. “Early 2026” is enclosed by January 1 and the verified source-public date, March 12. Those conventions are explicit in every observation. Unknown pause and snapshot-entry dates stay missing. The publication date is a conservative verified availability clock, not a claim that no earlier disclosure existed.

`milestone_vintages` filters every version at the requested source-public origin before comparing event windows. Future targets are permitted as targets; future historical milestones, malformed windows and missing public clocks are rejected. A target-window change is not a historical completion conflict. Repeated historical claims do not create additional transition events.

## Discovery registry correction

The previous registry used insertion-order deduplication. The revised `discovery_roster` selects the earliest source clock visible at the origin, keeps undated candidates explicit and excludes future-public versions. A retrospective 2016 event disclosed in 2026 cannot outrank an actual 2024 source. `archive_first_documented_public_date` describes visibility in this selected archive, not the true first announcement or state entry. An order-reversal regression test verifies this correction. The complete version ledger is preserved.

## Observation audit and estimability

The 60-record discovery ledger contains 28 adjacent observed pairs after information filtering and sorting by recorded valid/public clocks. Fifteen are same-state reobservations; ten are permitted endpoint pairs; three omit intermediate states or require definition review. Twelve pairs lack an event window at one or both endpoints; one overlaps or reobserves the same event window. These are diagnostics of this selected archive, not estimates of frequencies in a project population.

The three skipped cases are Lynas Malaysia heavy separation F→Q, Mt Weld expansion A→Q, and Upton F→C. They do not establish physically impossible jumps. Intermediate financing, construction or permitting observations are missing. The model's legal transition graph is not relaxed to fit them.

A known endpoint probability over h quarters integrates hidden paths, `(P**h)[a,b]`. A first-exit likelihood additionally requires survival up to the exit interval, a known entry/risk clock, the first exit cause and the observation protocol. Two press releases, an allowed endpoint pair, or a news-free quarter do not supply those conditions. No first-exit spells are admitted from this ledger. No population hazard or reporting-delay parameter is estimated.

`scripts/audit_project_observations.py` creates 44 quarterly **disclosure inventory** origins from 2016Q1 through the freeze. It counts source-visible records, activities ever documented and newly disclosed retrospective records. It does not carry a last reported state forward as physical survival. Physical projects-at-risk and known-survival exposure are missing throughout. The final 2026Q4 origin ends on October 11 and is flagged incomplete. Missing research coverage is not zero industrial capacity, project cancellation or deliberate policy opacity.

## Files and dictionaries

All tables below are under `data/processed/project_histories/`:

| Table | Interpretation |
|---|---|
| `milestone_versions.csv` | Stable record/milestone/project/activity IDs; observation kind; native date phrase; coarse outer bounds; public clock; exact quote/regex locator; source hash; interpretation. Includes targets and unknown-date pauses. |
| `state_observations.csv` | Five source-backed states aligned to the existing four-stage roster. `state_entry_event_verified=False` prevents automatic entry-time interpretation. |
| `latest_visible_milestones.csv` | Latest information version per milestone. A later version does not resolve the truth of a flagged conflict. |
| `milestone_revision_audit.csv` | Visible-version counts; disjoint reported historical windows; changed target windows; unresolved timing adjudication. |
| `state_pair_audit.csv` | Adjacent observed pair IDs/states, graph classification, missing/overlapping windows, and first-exit protocol rejection reason. |
| `quarterly_disclosure_inventory.csv` | Origin date, quarter-completeness flag, visible/new/retrospective source records, and explicitly missing physical risk/exposure counts. |

Figure: `outputs/empirical/rare_earths/upton_milestone_vintages.pdf`. Diagnostics: `outputs/diagnostics/project_history_validation.json` and `project_observation_audit.json`. Tests: `tests/test_history_observations.py`. The default replication executes both new scripts.

## Exact acquisition blocker and next observations

Archived SEC submission metadata identify RER Q2 2026 Form 10-Q, filed **2026-08-04**, accession **0001419806-26-000011**, primary document **reemf-20260630x10q.htm**, CIK **1419806**. The official SEC archive request failed with CONNECT 403; `metadata/project_history_acquisitions.jsonl` preserves the URL and error. Its text has not been read. Retrieve it to review commissioning/rework/output updates, alongside the three other unavailable quarterly filings in `docs/industrial_evidence_review.md`.

Next obtain contemporary start/pause/resume/qualification records, event-definition adjudication, independently observed state-entry/risk clocks and a systematic eligible cohort including failures. Several archived Pensana annual reports and Iluka's half-year financial report also lack verified public clocks in the source index; document signatures, fiscal dates and filename paths alone cannot supply those clocks. Do not fit duration or opacity-response parameters by quarterly-expanding the present selected snapshots.
