# SMIC operating scale and measurement review

Freeze: 2026-10-11. This continuation resumes release 5752124 and extends the independently measured semiconductor component (§6), without calibrating target capability, foreign access or national payoffs from aggregate production.

## Source coverage and clocks

Four original issuer earnings PDFs for FY2022–FY2025 are hash-verified and reparsed directly. Their first-page issuer datelines are 2023-02-09, 2024-02-06, 2025-02-11 and 2026-02-10. The dateline, reporting period and conference-call date are distinct. The legacy financial builder now requires the release date on PDF page 1, rather than accepting a matching date anywhere in the document. Existing financial values and public dates are unchanged. Present original-byte support does not independently certify historical release-time bytes or a globally earliest disclosure.

The new dataset has **120 source-vintaged numerical observations**, **12 unit/denominator definitions** and **four release-clock records**. There are 96 latest cells, covering nine distinct selected quarters plus annual summaries. Twenty-four comparative groups retain separate source versions. This is a sparse, selected consolidated-firm sample, not a continuous quarterly panel or 120 independent observations.

| Variable group | Native unit / window | Interpretation |
|---|---|---|
| `wafer_shipments` | Reported equivalent wafers per quarter | Preserve generic versus standard-logic 8-inch wording; not chips/dies or advanced-node throughput |
| `monthly_capacity` | Reported equivalents/month for a quarter; exact rate measurement day unknown | A rate snapshot, not quarter-total production or the average quarterly denominator |
| `capacity_utilization` | Percent over an issuer-estimated quarter denominator | Numerator is wafers out, not necessarily shipments |
| `annual_utilization_summary` | Issuer annual/annualized percent summary | Separate from Q4 utilization; exact annual weighting is not reconstructed |
| `rounded_yearend_monthly_capacity` | Thousands of reported equivalents/month | Summary presentation, distinct from the detailed unit-level sentence |
| `total_revenue`, `rd_expense` | Nominal USD thousands per quarter | Financial measures, not technology scores or real investment effort |
| `capital_expenditure` | Reported nominal USD millions per quarter | Preserve reported category; not independently reconciled project cash deployment |
| Service revenue shares | Percent of total revenue | Wafer versus other service revenue, not physical output shares |
| 8-/12-inch revenue shares | Percent of wafer revenue | Not wafer-count/area shares, node shares or target capability |

`period_end`/`valid_date` index the reporting period, rather than asserting a precise rate measurement day; `info_public_date` is the exact source's issuer-stated dateline. `measurement_timing` separates flows, rate endpoints, quarterly ratios and annual summaries. `pdf_page`, `locator`, `quote`, `header_quote` and `source_cell_token` bind quantities to the original named row and period columns. Source URL, SHA256 and retrieval time are retained. Definition adoption dates and comparative conversion history remain unknown.

The FY2023 own-quarter shipment label is generic 8-inch equivalents. Its unchanged 2023Q4 comparative number appears under standard-logic wording in the FY2024 source. The utilization note also changes from explicit 8-inch-equivalent wafers out to total wafers out without specifying the basis in that note. These are **two definition-wording changes**, not two proved industrial or calculation-method changes. No conversion factor or adoption date is invented. Latest-by-freeze charts use each selected reporting vintage's wording, including retrospective comparatives; colors do not date a transition.

## Executed results and valid identities

Q4 2025 reported shipments are **2,514,970 standard-logic 8-inch equivalents**, reported monthly capacity is **1,058,750 equivalents**, and quarterly utilization is **95.7%**. The management annual/annualized summary is **93.5%**. Twelve-inch wafers contribute **77.2% of wafer revenue**. None of these measures identifies indigenous tool content, advanced-node yield, a qualified target production envelope or usable foreign access.

Twenty-four revenue-share sums reconcile to 100%. Four detailed-versus-rounded capacity comparisons are consistent within half a displayed thousand-unit increment. This is a conditional presentation check, not a measured capacity uncertainty interval or confidence interval. Four own-source/own-year Q4 R&D observations match the legacy financial extraction. No identity equating three times the reported monthly capacity rate times utilization to shipments is imposed: estimated quarter-average capacity, wafers out, inventories and revenue-recognition timing are different objects.

For each original release and each of its three quarter columns, reconstruct reported wafer-attributed nominal revenue as total revenue times the reported wafer-service share. Divide by reported equivalent shipments to obtain a descriptive unit revenue ratio. Its log change plus the log shipment change equals the reconstructed log wafer-revenue change. **Eight within-source comparisons** (QoQ and YoY for four releases) satisfy this algebraic identity, with maximum absolute residual about 2.22e-16. It is an accounting construction using rounded shares, not an independent economic validation or estimated production function.

In the FY2025 release's Q4 year-on-year comparison, reported shipments rise **26.3%**, reconstructed nominal wafer revenue rises **12.6%**, and nominal revenue per reported equivalent shipment falls **10.8%**. All four source-year comparisons are retained. The ratio cannot isolate pricing, product mix, quality, equivalent-unit conventions or recognition timing and is **not a quality-adjusted wafer price**. No causal control effect, domestic substitution elasticity or target-capability score is inferred.

## Failed acquisitions, repairs and remaining evidence

The archived issuer index contains exact links to two 2026 quarterly candidates:

- `https://smic.cdn.shwebspace.com/uploads/6a057e3f/ER_EN.pdf`
- `https://smic.cdn.shwebspace.com/uploads/6a7d7c4f/ER_EN.pdf`

Both failed CONNECT 403. `metadata/smic_operations_acquisitions.jsonl` preserves the discovered original link, discovery-source hash and actual failed response. No PDF content or publication clock is assigned, and no 2026 observation is admitted from them. Do not retry an unchanged denied route without a meaningful access change.

The initial legacy R&D integration check incorrectly paired a prior-year comparative with the current-year input from the same report. The retained failed diagnostic is `outputs/diagnostics/smic_operations_initial_crosscheck_failure.json`. The repair matches source and reporting year, without changing source values or relaxing numerical tolerances. Historical comparatives remain in their own period and source-vintage audit.

The shell transport disconnected during initial inspection and once during editing, then recovered on fresh supported Bash requests; no blocked extraction is claimed as executed. The tested pipeline provides the final execution record.

Required next evidence: contemporaneous quarterly releases, independent historical source vintages, normalization-method history and adoption dates, stable target-node/product yield and qualification, indigenous versus imported equipment/EDA/metrology/memory/packaging content, installed foreign servicing/parts/license access, frozen pre-policy exposure weights and a defensible comparison panel. One firm and nine selected quarters cannot resolve anticipation, cycles, subsidies, spillovers or endogenous treatment selection. Aggregate production and spending leave the blueprint's z/f/a and game x unmeasured. Independent engineering/coder review remains necessary.

## Rebuild

Run `uv run python scripts/run_semiconductors.py`, `uv run python scripts/build_smic_operations.py`, then `uv run python scripts/analyze_smic_operations.py`. The end-to-end DAG runs all three in that order. The original-source audit reparses named cells, source headers, units, definition versions and first-page clocks from immutable originals, with explicit PDF page locators. Figures and `manuscript/smic_operating_changes.tex` are generated from executed data. Synthetic/scenario outputs remain separate.

Rate timing refinement: detailed monthly capacities are associated with their reporting quarter; an exact measurement day is not inferred from “in Q3/Q4.” `valid_date` indexes the reporting-period endpoint. Rounded management summaries explicitly referring to year end retain that distinct timing. No quantity or source/publication clock changed.

## Manuscript release failure and repair

The initial current-container run passed 297 tests and 1,966 data checks, with all 68 selected artifacts byte-identical, but **failed** the final manuscript comparison. All thirteen normalized-text differences were stale table-of-contents page numbers; the body text and economic quantities matched. The final container TeX log retained “Label(s) may have changed. Rerun to get cross-references right” despite a zero latexmk exit. Original failure evidence is retained in `outputs/diagnostics/smic_operations_initial_release_failure.json`, `smic_operations_manuscript_text_differences.json` and `smic_operations_initial_container/`. This failure was not waived or normalized away.

The build now uses latexmk for dependencies/bibliography, then forces final pdfLaTeX passes until the `.aux`, `.toc`, `.out` and `.bbl` hashes are unchanged across an actual pass and the final log has no unresolved citations/references, rerun requests, overflow or fatal error. At most six settling passes are allowed; failure stops replication. Seven diagnostic regressions include the observed warning and line-wrapped undefined citations. `scripts/build_manuscript.py` exposes the same build for a manuscript-only rebuild. The final release checker requires both convergence reports and actual extracted-text identity. Consult current `manuscript_convergence.json`, `container_extension_manuscript_convergence.json` and `final_release_validation.json` for the rerun outcome; the initial failed report is not a passing release.

Final executed release evidence (2026-10-20 UTC): host and disconnected container each passed 304 tests and 1,966 checks; all 68 compared artifacts and 162 code/configuration/test files matched. Both converged 37-page PDFs have identical extracted text. Host pipeline: 220.27 seconds; container: 223.24 seconds. Final release passed; see `outputs/diagnostics/final_release_validation.json`. Large-game arrays were re-audited, not re-solved, and the numerical core remains unchanged. These checks do not certify independent historical source vintages, a second-machine replication or empirical publication readiness.
