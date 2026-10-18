# Strategic Policy Opacity Index: implemented method and evidence boundary

Authority: blueprint Sections 2, 7, 10, 11, and 14. Freeze: 2026-10-11. This module measures observable information conditions and cannot establish strategic intent.

## Executed findings

`tests/test_opacity.py` executes the ten rubrics, publication/effective/event clocks, immutable vintage selection, daily pillar gates, and quarterly calendar-day denominator. Latest execution: **26 tests passed**. Two fully synthetic vectors reproduce **57.41666666666667** and **16.75**. Synthetic equal-ten-indicator arithmetic for the former vector is 57.5; it is a sensitivity specification rather than the principal index. The first equality test used exact floating comparison against 57.5 and failed on 57.49999999999999; it was corrected to a numerical tolerance and rerun. No scientific criterion was relaxed.

`python scripts/run_opacity.py` evaluates 649 calendar days, 2025-01-01 through the freeze. **Zero source-adjudicated indicator cells, zero valid days, and zero valid quarters** are present. This is an evidence-availability result, not evidence of high or low Chinese opacity. No daily or quarterly headline empirical SPOI is reported. The empty legal-event count is researcher-missing; the separate recorded-event count reports database contents only.

The independently double-coded field sample is unavailable. The weighted Cohen kappa implementation and paired-bootstrap confidence interval execute on explicitly synthetic data in tests. No field-reliability coefficient is claimed. No lagged opacity–project hazard regression, nonlinear investment turning point, causal effect, or empirical factor model can be estimated from the current inputs.

## Source acquisition and legal records

`metadata/opacity_sources.csv` records source IDs OP-18-EN and OP-70-ZH, requested URLs, retrieval timestamps, and actual failures. Initial requests through the original HTTPS proxy policy failed with tunnel 403 responses. Following the root agent's domain-configuration update and successful unrelated official-source checks, meaningful retries yielded **HTTP 503** for the corrected No.18 English page and **HTTP 403** for the No.70 Chinese page. Search-engine requests also failed through the proxy. No TLS verification was disabled, no bytes were fabricated, and no unsuccessful response is represented as an archived source. Blank hashes and archive paths mean no artifact was acquired. The raw-source directory consequently contains only this provenance explanation.

Blueprint R31 ends with `.html%3A11`; the encoded `:11` suffix is not part of a normal HTML artifact path. The acquisition removed that suffix, retaining the rest of the blueprint URL. This repairs a malformed locator syntactically; it does **not** independently establish a canonical Chinese-language legal URL or verify the document. Both canonical legal texts remain required. `data/processed/opacity/blueprint_unverified_candidates.csv` preserves blueprint candidate dates, explicitly excludes them from estimation, and distinguishes them from sourced observations. The source manifest's `blueprint_claimed_public_date` is separate from its blank verified `info_public_date`.

If originals become available, the legal coder must verify item-specific scope, publication and effective dates, amendments, exemptions, licensing procedures, and suspension targets. No.18 must not be treated as a blanket Nd/Pr export prohibition. Whether No.70 leaves No.18 operative requires original-text adjudication; the blueprint's stated inference is not an independent legal observation. A relaxation or suspension is not automatically an adverse O6 reversal. Typography is excluded from O10, and cross-agency copies of one intervention are deduplicated.

## Locked rules and implementation choices

`codebooks/spoi_codebook.csv` preserves all ten ordinal anchors. `configs/opacity.yaml` locks 40/35/25 pillar weights, 90-day event memory, 30-day release grace, at least 8/10 observed items, disclosure >=3/5, predictability >=2/3, clarity >=1/2, and >=80% valid calendar days per quarter. The daily score keeps the original pillar weights and normalizes only over observed items within each pillar. It never redistributes an unavailable pillar's weight, imputes midpoints, or carries headline scores forward.

- O1 is the worst lateness among known active obligations. Lateness accumulates from the original due date; a verified continuing absence at the next reporting cycle scores 4. Released completeness/lateness persists only in the registered observation window. The investigator must distinguish a continuing unfulfilled obligation from an expired reporting window; the latter is not silently extended.
- O2 pools required-field counts over the current registered releases. O3 pools expected license-statistic item counts only where a series or disclosure duty is documented. A failure to retrieve a release is researcher-missing, not an affirmatively absent release. Zero denominators are not applicable.
- O4 takes the worst substantive, still-active event first public in `(d-90,d]`. It uses actual publication-to-effective calendar-day gaps; a negative gap scores 4. A missing effective date remains researcher-missing. An elapsed recent-event stock is zero only after the policy-event search universe has been adjudicated.
- O5 persists for effective public rules until exclusive `end_date`. The preregistered principal aggregation is **worst active instrument**; the optional exposure-weighted aggregation rejects missing/nonpositive or post-policy weights. Instruments retain separate rows and source adjudications. Product, target/use, procedure, and review criteria are the four fields.
- O6 is observed from publication and retained until 90 days after the later of publication and effectiveness, without retrospective public knowledge. An anticipated reversal without a public announcement receives no invented earlier warning.
- O7 uses written minor/material adjudication and a 90-day post-resolution window. The resolution's own public date prevents hindsight from shortening a historical conflict stock. The rubric's phrase **“material no resolution” is ambiguous** beside the 1-material and 2-material anchors; the implementation therefore requires an explicit `material_no_resolution` adjudication flag and never infers it merely because a conflict remains open. Empirical use requires a registered resolution/materiality protocol and independent coding before this flag may be used.
- O8 uses scheduled due-plus-grace checkpoints in the previous 365 days. A publication after a checkpoint remains missed at that checkpoint even if later available. Missing retrieval coverage is distinct from verified absence. Grace sensitivities are 0 and 90 days.
- O9 requires a frozen official record universe and **one documented comparable measurement unit and basis**. Mining, oxide, alloy, and finished-magnet tonnes cannot be silently pooled. A table with incompatible bases remains researcher-missing until a defensible source-supported denominator is constructed.
- O10 counts distinct material interventions once they are both public and effective, using `max(publication,effective)` in `(d-90,d]`. Purely typographic events do not count.

The event no-event rules require dated, adjudicated search coverage in `source_events.csv`; an empty database alone does not establish that no event occurred. This is an implementation guard against equating missing research with transparency and does not change the blueprint's zero-event rubric. Scheduled duties without an objective denominator return `not_applicable`; a documented but uncollected item returns `researcher_missing`; both have explicit reasons and no numeric score.

`window_sensitivity` executes all combinations of 30/90/180-day memories and 0/30/90-day grace. `alternative_weights` supplies equal pillar and complete-ten-indicator comparisons. Exponential-decay or latent-factor sensitivity requires a registered decay parameter or validated ordinal factor specification, respectively; neither is estimated from absent data. No constant synthetic index is used as empirical validation.

## Data dictionary and entry requirements

All files under `data/processed/opacity` are UTF-8 CSV. The three live input tables are currently header-only; candidates are a separate excluded file.

| Table | Key fields and units | Entry rule |
|---|---|---|
| obligations | `obligation_id`, `record_version_id`, `info_public_date`, `due_date`, exclusive `observation_end_date`, `next_due_date` | Record each scheduled release separately; preserve revisions. Duty/expected denominator requires `denominator_source_id`. |
| obligations evidence | `release_date`, `release_info_public_date`, `affirmatively_absent`, `absence_verified_on` | Release and absence must be independently substantiated; an inaccessible page is not affirmative absence. |
| obligations metrics | `missing_required_fields/required_fields`, `available_license_metrics/expected_license_metrics`, `classifiable_throughput/total_documented_throughput`, `measurement_unit`, `measurement_basis` | Fractions must be in [0,1]; denominator must be known and positive. O9 quantities require comparable units and bases. |
| legal_events | `event_id`, `record_version_id`, `event_type`, `publication_date`, `effective_date`, `info_public_date`, exclusive `end_date`, `source_id` | Types: new_policy, adverse_reversal, amendment, legal_rule, conflict. Record separate linked rows for distinct measurement roles. |
| legal event adjudications | `substantive`, `material`, `intervention_id`, `explicit_scope_fields`, `materiality`, `material_no_resolution`, `resolution_date`, `resolution_info_public_date` | Independent intervention IDs deduplicate agencies; explicit fields is integer 0–4; materiality minor/material; resolution has a separate public clock. |
| optional weights | `frozen_exposure_weight`, `weight_info_public_date` | Registered pre-policy exposures only. |
| source_events | `coverage_id`, `kind=coverage`, `indicator` (O1–O10 or ALL), `info_public_date`, inclusive `valid_from`, inclusive `valid_until`, `adjudicated`, `source_id` | A search protocol and archived evidence establish the covered event/obligation universe. Retrospective research completion cannot masquerade as earlier public availability. |
| daily output | O1–O10 plus `_status`, `_reason`, `_numerator`, `_denominator`; pillar counts/scores, validity, `spoi` | Score range [0,4], principal index [0,100]. NA and researcher-missing remain distinguishable. |
| quarterly output | calendar/recorded/valid days, coverage, validity, SPOI, maximum, event counts, per-indicator observed days | Full calendar denominator even for a partial final quarter. Fewer than 80% valid days gives a missing headline. |

## Exact remaining requirements

1. Acquire lawful authoritative No.18 and No.70 legal artifacts and verify Chinese-language canonical locators, dates and legal scope against archived bytes/checksums.
2. Establish the complete China/rare-earth policy event universe, materially adverse reversal definition, and cross-agency amendment IDs, including no-event search coverage.
3. Establish dated release calendars and institutional duties for O1/O2/O8; documented license-statistic series or duty for O3; a frozen, comparable official capacity/output denominator for O9. Too few true duties may make the blueprint's main index inapplicable, even after exhaustive research.
4. Write a materiality/resolution protocol, resolve the O7 ambiguous anchor prospectively, and obtain independent blinded coding (O5/O6/O7 plus stratified other items), with agreement and confidence intervals against target weighted kappa >=0.75. A second model pass is not claimed as independent human reliability.
5. Link coverage-valid lagged quarterly scores to a validated project transition risk set, documented support, technology uncertainty and market/geopolitical controls. Assess attrition, temporal support, dependence and statistical power before estimation. The implemented gate reports the missing regressors and risk set instead of manufacturing coefficients.
6. A positive quadratic alone will not establish overreaction: its turning point must lie in observed support (preferably 5th–95th percentile), uncertainty must reject opposite shapes, and missingness/nonparametric sensitivity must survive. Government support remains nonrandom; no causal or motive interpretation is authorized without a separate credible design.

## Reproduce

From the repository root after locked dependency installation:

```
.venv/bin/pytest -q tests/test_opacity.py
.venv/bin/python scripts/run_opacity.py
```

Outputs reside in `outputs/empirical/opacity` (availability/coverage only) and `outputs/synthetic/opacity` (clearly labeled rubric figures/tables). The module manifest lists input/output SHA256 values. No network request occurs in the analysis script. Field acquisition, adjudication and independent coding remain required external evidence steps, rather than hidden inference defaults.
