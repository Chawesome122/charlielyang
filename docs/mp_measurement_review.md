# MP production, sales and inventory measurement review

Information freeze: 2026-10-11. This continuation resumes release c29d541. All new economic observations come from three existing hash-verified original MP SEC filings, not a newly retrieved technical report. Present source-byte support does not independently certify the bytes originally available at each historical release.

## Evidence and definitions

The original FY2023, FY2024 and FY2025 reports became public on 2024-02-28, 2025-02-28 and 2026-02-26, respectively, according to the existing verified filing registry. Every comparative cell retains that report's public clock. An older economic period does not make a later comparative available earlier. The source universe is incomplete and is not all public contemporary information.

The extraction contains 174 native cell versions: 36 annual production/sales KPI cells, 96 quarterly KPI cells and 42 monetary inventory cells. It separately preserves 19 definitions, 38 N/A cells and two displayed dashes. There are 58 multi-source comparative groups, with no changed source tokens among the selected cells. Matching numbers do not establish unchanged definitions.

| Field | Meaning |
|---|---|
| `period_end`, `valid_date` | Reported annual/quarterly flow period end, or inventory measurement date |
| `info_public_date` | That exact source filing's verified release date |
| `variable`, `product_basis` | Named KPI or inventory category, preserving REO content, NdPr oxide production and oxide-equivalent sales distinctions |
| `table_kind` | Annual KPI, quarterly KPI, or monetary inventory |
| `native_unit` | KPI metric tonnes, or USD thousands; never a universal material quantity |
| `value`, `cell_status`, `source_cell_token` | Reported number, N/A or dash; the latter two have missing numerical values |
| `comparative` | Prior-year cell in a later source, not an independent new physical observation |
| `table_ordinal`, `row_ordinal`, `locator`, `quote` | Original HTML table/header/row context, with exact original quotation |
| `source_id`, `source_sha256`, `source_url` | Original-byte provenance; retrieval timestamp is retained in the source registry and native cells |

Definition `valid_date` is a public-source snapshot, not an inferred date of convention adoption. The one explicit internal-sales condition states Q4 2025; the quarterly interval is not an exact transaction date. Adoption of the assumed conversion convention and reconstruction of earlier comparative sales remain unknown.

The original document describes upstream production as contained REO in concentrate, including material subsequently fed to downstream circuits from Q2 2023. NdPr production is finished and packaged oxide. These are overlapping stages and cannot be added. The target of greater than 60% REO per dry concentrate tonne is not a measured wet-feed assay, current stock or realized recovery.

NdPr sales are an oxide-equivalent revenue-recognition KPI, potentially representing either oxide or metal. FY2023 illustrates a hypothetical 1.25 oxide-equivalent/metal ratio; FY2024/FY2025 state an assumed 1.20 ratio. This is not measured recovery, exact chemical stoichiometry or proof of a historical conversion change. From Q4 2025, Materials sales include internal transfers to Magnetics. External-customer volume is not separately identified by this KPI. Transit, conversion timing and actual versus assumed yields can affect the production/sales gap.

## Executed descriptive results and unresolved identities

Calendar 2025 native REO-content production/sales are 50,692 / 8,922 KPI tonnes. NdPr finished-oxide production is 2,599 tonnes; oxide-equivalent sales are 1,994. Their numerical difference, 605, is **not** an identified physical stock increase. The source's monetary inventory balance is USD 252.099 million in total, including USD 39.622 million in current finished goods; neither quantity supplies element-specific physical inventory. A missing Magnetics operating KPI does not establish zero production.

Twenty-four quarter/annual comparisons have three distinct outcomes: 14 exact numerical identities, six all-N/A classification checks, and four incomplete comparisons containing early N/A quarters despite a numerical annual value. No N/A is filled with zero. Twelve currency inventory component identities reconcile. None is independent measurement of industrial performance.

The initial builder incorrectly required every comparison to be numerically testable and exited with failure. Its diagnostic is retained at `outputs/diagnostics/mp_measurement_initial_reconciliation_failure.json`. The repair reports incomplete comparisons with a nullable pass result, retaining their missing quarter sums. Only explicitly numerical discrepancies fail an identity; an untestable comparison is not counted as a passed numerical identity. The exact-discrepancy regression check still rejects a one-tonne inconsistency. This changes audit semantics, not source values or tolerances.

## Historical baseline comparison

The codebook freezes 19 quarter-end origins from 2021Q1 through 2025Q3 and a next-quarter horizon. There are 76 candidate origin/metric pairs, of which only nine have common numerical support for all three naive methods: three each for REO production/sales, two for NdPr production and one for NdPr sales. These span just three calendar origins in 2024. Missing/N/A/dash seasonal observations are not replaced with zeros. The current selected originals supply no quarterly 2025 KPI table.

Persistence, previous-year seasonal and available-history-mean predictions are executed. Training uses only cells publicly available by the origin. Evaluation uses the latest archived comparative cell available by the freeze, explicitly not first-release accuracy. The later-comparative perturbation test changes evaluation actuals without changing earlier predictions. The complete eligibility attrition is in `outputs/empirical/rare_earths/mp_quarterly_origin_audit.csv`; scores are in `mp_quarterly_baseline_scores.csv`. One to three dependent origins do not establish statistical superiority, calibrated uncertainty, producer-level structural forecasting skill or system-service skill. No causal effect or fitted adaptation parameter is reported.

## Rebuild and remaining evidence

Run `uv run python scripts/build_mp_measurement.py`, then `uv run python scripts/analyze_mp_measurement.py`. The end-to-end DAG runs both. `scripts/audit_original_quotes.py` independently reopens each original snapshot and rechecks table kind, annual/quarterly headers, row label, cell token/value, unit, missing-state and source clock. The two figures and LaTeX baseline table are regenerated by the analysis script.

The exact FY2025 incorporated technical report was requested from `https://www.sec.gov/Archives/edgar/data/1801368/000180136826000008/mpmcexhibit961123125.htm` and failed CONNECT 403. Its original source link and failed request are in `metadata/mp_measurement_acquisitions.jsonl`; no contents, assays or recoveries are claimed from it. Do not retry the unchanged denied route without a meaningful access change.

Next requirements: acquire original technical/quarterly documents; independently establish historical publication vintages; adjudicate convention adoption and comparative restatements; measure element assays, physical feed allocation, dated opening stocks and full stock-flow bridges; separate external versus internal transfers; obtain qualified stable downstream throughput, route limits, ownership/origin and grade demand. These data are necessary before these disclosures can constrain an empirical China-free service LP. Population project hazards, semiconductor functional/access measurements, SPOI coding and the continuous-game certificate remain independent unresolved requirements.
