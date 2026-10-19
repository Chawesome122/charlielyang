# White Mesa native feed, product, inventory and capacity evidence

Information freeze: **2026-10-11**. This continuation uses three already archived Energy Fuels original Forms 10-K. Their verified conservative filing clocks are February 23, 2024; February 26, 2025; and February 26, 2026. No independently archived release-time binary or globally earliest disclosure is certified.

`codebooks/white_mesa.json` defines **49 claims**. `scripts/build_white_mesa.py` checks the source clock, extracts the same hash-verified original-byte snapshot, matches the exact curated phrase and binds numerical values to named regex groups. All native values, units, product forms, roles, periods, source IDs, hashes, public clocks and quotations survive in the data. These are within-issuer disclosures, not a representative project population or independently measured production.

## Actual flows and product-form issue

| Reported period/episode | Source vintage | Processed monazite | Reported product |
|---|---|---:|---|
| 2021 | FY2023 | 400 native tons | 120 tonnes contained TREO in RE carbonate |
| 2022 | FY2023 | 184 tonnes | 95 tonnes contained TREO in RE carbonate |
| 2023 | FY2023 | 326 tonnes | 260 tonnes contained TREO in RE carbonate |
| 2024 commissioning run | FY2024 | 500 tonnes | 38 tonnes described as NdPr **oxalate** |
| Same described 2024 run | FY2025 | 500 tonnes | 38 tonnes described as NdPr **oxide** |

The first source's rounded glossary says one metric tonne equals 1.102 tons. It does not establish an exact ton standard; the generic 2021 tons remain native rather than being silently converted with an exact U.S.-short-ton factor. Four unit-matched product/feed comparisons are approximately 0.516304, 0.797546, 0.076 and 0.076; the 2021 metric ratio remains missing. These are arithmetic comparisons of rounded/approximate issuer quantities; decimal digits do not establish physical measurement precision or confidence intervals. They divide native product or contained-oxide-equivalent quantities by bulk feed. Assays, inventory carry, auxiliary material and full processing balances are unknown, so **none is a chemical recovery, utilization rate or service fraction**. An MP concentrate grade cannot substitute for a White Mesa monazite assay.

The oxalate/oxide descriptions are not independent additional batches. Their equal numbers do not identify an equivalent mass or authorize a chemical conversion. A process-stage or oxide-equivalent convention could explain the wording; operator/technical evidence is required before deciding. Source versions are filtered at each public origin and retained without choosing a later description as historical truth.

The legacy research table had called the generic 38-tonne output and 800/1,000 nominal-capacity observations `separated_NdPr_oxide`, although their matched generic phrases did not establish that mass basis. All three research labels are corrected to `separated_NdPr_reported_product_form_unconfirmed`. Values, source quotes and public clocks remain unchanged. `basis_corrections.csv` documents the earlier label, corrected label, record ID, source hash and reason. This is a **research coding correction**, not a new issuer announcement or backdated source revision. The merged Phase 1 discovery record also retains the form caveat.

## Inventories, work in process and sampling sales

The FY2025 report explicitly dates approximately **34 tonnes of separated NdPr inventory at December 31, 2025**. It reports **1.7 tonnes of 2025 sampling sales** to POSCO International, with the disclosed material meeting that recipient's applicable specifications. This does not establish universal qualification, independent magnet-production capacity or a separate additive batch alongside the previously coded Korean demonstration.

The same source says the company has **26 tonnes NdPr and four tonnes Sm+ RE carbonate in solution**. That additional sentence does not independently date the measurements. The prior report similarly describes **28 tonnes NdPr and four tonnes Sm+ in solution**, again without a separately explicit measurement date. These four WIP claims use a source-date snapshot with `measurement_date_known=False`; the source-public date is not substituted for an observed stock-measurement date. Annual flows retain their explicitly stated reporting periods. Only the 34-tonne finished-stock statement has an explicit stock date.

No stock is added to historical production or sampling sales. No balance is forced by treating historical production as opening inventory, assuming zero subsequent production, or ignoring samples/transfers and process stocks. A missing balance component stays missing.

`stock_origin_audit.csv` applies **20 checks**, combining five stock disclosures with four origins. It separately checks publication, explicit measurement date, a dated bridge to the origin, finished/separated product role and verified physical form. No current finished/separated opening stock is admitted under the available evidence. The admitted quantity is **missing, not zero**. WIP would require a separate dated intermediate-commodity ledger, composition and processing recipe before an LP could use it. The inventory statement was unavailable at its own December 2025 measurement origin; after publication it is an older observation requiring a stock-flow bridge. None becomes an October 2026 stock automatically.

## Capacity components and shared resources

The FY2025 expected-capacity table reconciles three native product columns:

| Product label | Phase 1 component | Planned Phase 2 | Combined table total |
|---|---:|---:|---:|
| NdPr | 1,049 | 5,513 | 6,562 |
| Tb | 12 | 48 | 60 |
| Dy | 35 | 165 | 200 |

Native time basis is tpa. Phase 1 NdPr is labelled existing, while its HREE additions are planned. The whole table is conditional expected capacity with an explicit “actual recoveries may differ” footnote. Three exact sum identities verify the displayed arithmetic; they do not verify operating rates. Dashes mean no displayed component for that cell, not observed zero production. Combined totals are never added to their components, and different product columns are not summed.

The filings also preserve design ranges and their changes: Phase 1 monazite throughput of 8,000–10,000 tonnes/year; TREO ranges of 4,000–5,000 versus 4,000–6,000; NdPr ranges of 800–1,000 versus 850–1,000, with their respective source/form contexts. The detailed expected table is not silently substituted for these design statements, and none is treated as achieved annual output or an estimated probability distribution.

The crack/leach front end is shared with uranium, allowing only one feed at a time. This is an instantaneous exclusivity statement. Annual time sharing can be feasible, but requires campaign schedules, processing rates, changeover constraints and material balances. A licensed annual uranium-output quantity in pounds cannot be turned into a monazite-feed machine rate. No independent full-capacity lines or unconstrained upstream feed are introduced.

The engineering discussion states full commissioning in Q2 2024 and initial commercial-run completion in Q3; the accounting description states construction/commissioning completion in Q3. The claims retain their different definitions and native-quarter outer enclosures. They do not establish an error, exact completion date, suspension or admissible first-exit spell.

## Files and replication

Under `data/processed/white_mesa/`:

- `observations.csv`: 49 source/version-linked claims with role, date/period, product, native unit and exact quote.
- `reported_flow_ratios.csv`: five paired source comparisons, four numerical and one unit-blocked; recovery/utilization/service remain missing.
- `stock_origin_audit.csv`: 20 information/date/bridge/form/role checks; no invented opening stocks.
- `capacity_component_identities.csv`: three same-product identities, with conditional-plan and nonadditivity flags.
- `product_form_versions.csv`: public-origin masking of the 2024 episode's different form descriptions.
- `basis_corrections.csv`: three explicit research-label corrections with unchanged values/source dates.

Run `scripts/build_white_mesa.py` after `scripts/build_rare_earths.py`. Both it and `scripts/plot_white_mesa.py` are included in default replication. Diagnostics: `outputs/diagnostics/white_mesa_validation.json`. Tests: `tests/test_plant_ledger.py`. Figures: `outputs/empirical/rare_earths/white_mesa_native_flows.*` and `white_mesa_capacity_components.*`. The original-quote audit now includes these new claims.

Two genuinely new exact incorporated technical-report URLs were attempted: Vara Mada `https://www.sec.gov/Archives/edgar/data/1385849/000106299326000229/exhibit99-1.htm` and Donald `https://www.sec.gov/Archives/edgar/data/1385849/000106299326001182/exhibit99-2.htm`. Both failed CONNECT 403. `metadata/white_mesa_acquisitions.jsonl` preserves the attempts and their exact referring source. No contents or physical coefficients are attributed to the inaccessible originals.

Required next evidence: operator/technical reconciliation of oxalate/oxide and commissioning definitions; actual ton convention; dated opening/closing inventories and WIP/transfers; feed assays and element recoveries; line rates, utilization and campaigns; stock ownership/encumbrance; auxiliary origins, routes, qualification and grade-specific demand. These observations do not identify an empirical China-free network, population hazards, real-world threshold probabilities or a causal response.
