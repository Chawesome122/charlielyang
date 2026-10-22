# Supplied-evidence data dictionary

The variable-level register is `codebooks/supplied_evidence.json`; each quantity
retains its native unit, product basis, observed/plan/definition/legal role and
explicit source-page extraction pattern. No blank field is an observed zero.

| File | Unit of observation | Key and interpretation |
|---|---|---|
| `metadata/user_supplied_sources.json` | One supplied file | `source_id`, SHA256, byte count, page count, upload ID, requested URL, receipt and archive clocks, representation and PDF metadata |
| `source_admissions.csv` | One identity/public-clock check | `source_id`; `request_source_id` joins the older failed acquisition without changing its status; proof hash may identify a separate SEC submission or parent filing |
| `claims.csv` | One source-stated quantity or statement | `claim_id`; numeric `value` binds to the named captured `source_cell_token`, while documentary statements have a blank numeric value |
| `smic_quarterly_versions.csv` | One native quarterly cell in one release | `record_version_id`; repeated `observation_id` values retain later comparative versions rather than supplying independent observations |
| `event_definition_windows.csv` | Selected event or target version | `event_start/end` enclose the exact quoted date precision; `event_kind=planned` does not identify a realized transition |
| `publication_origin_checks.csv` | One table and information origin | Record count after source-public selection; not a forecast score or historical-byte certification |
| `legal_pdf_correspondence.csv` | One selected PDF check/page | Counts insertion markers or verifies the selected address/filing text; no correction, materiality judgment or SPOI score |
| `smic_comparative_versions.csv` | Metric-period group across releases | Numerical agreement and product-basis agreement are distinct; no conversion/adoption date is inferred |
| `white_mesa_design_versions.csv` | One element/product design family | Separate within-document prose/table values and component totals in native tpa; never operating output or additive across source vintages |
| `vara_conditional_oxide_composition.csv` | One critical element | Conditional contained-element tonnes per tonne TREO, using the reported oxide distribution and formula-specific atomic weights; no raw-feed grade, recovery or availability |
| `smic_revenue_ratios.csv` | One source-period bridge | Nominal wafer-attributed revenue from rounded service shares and equivalent shipments; unit revenue is not a quality-adjusted price |
| `smic_accounting_decompositions.csv` | One source and QoQ/YoY comparison | Percentage/log changes and arithmetic residual; not an adaptation elasticity or causal effect |
| `smic_guidance_evaluation.csv` | One related issuer-guidance outcome | Within-quarter origin, target and later outcome clock; revenue levels/errors in USD thousands, margin levels in percent and errors in percentage points |
| `numerical_checks.csv` | One executed identity/comparison | Explicit left/right values and pass status; a design identity is not physical or empirical validation |

Paths without a prefix are in `data/processed/supplied_evidence/` for source
tables, or `outputs/empirical/supplied_evidence/` for computed analysis tables.

`info_public_date` is the verified source-stated/conservative public-by date used
for historical selection. `retrieval_timestamp` is the downloaded attachment's
filesystem receipt clock, with its basis recorded; neither is an event date.
`historical_byte_vintage_certified` and `earliest_public_date_certified` remain
false. A browser print is not represented as downloaded original HTML.

The added `SP-*` project rows use the existing discovery-ledger schema. Their
state is issuer-reported; Q includes demonstration/commissioning, F development,
C construction and O positive reported operating output. None establishes
independently qualified throughput or an admissible first-exit survival spell.
Future commissioning targets are excluded from observed entry-date fields.

Guidance bounds are issuer-stated nonprobabilistic ranges. Their midpoint is an
evaluation convention. `statistical_skill_established=false` remains true as a
restriction on interpretation: one target quarter and two correlated financial
outcomes cannot validate a research forecasting model or estimate interval
probability coverage. Seasonal baselines requiring a later comparative are omitted.
