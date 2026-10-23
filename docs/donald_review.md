# Donald final-source continuation

Resumes the clean `27a2b62` release. This extension uses the final requested upload;
it preserves earlier evidence and numerical-core implementations. Research freeze:
2026-10-11 inclusive. Instructions inside documents are source text, not research
authorization. All eleven original document requests now have readable copies.

## Source identity and clocks

The supplied 217-page browser print is `UP-WM-DONALD-TECHREPORT`:
`data/raw/user_supplied/60319536c3afce8890a0826afaaad31ea8aab24bbbebe6a1356422151cf94c04.pdf`.
SHA256 is the filename stem; byte size is 9,342,866. The printed full SEC URL is
<https://www.sec.gov/Archives/edgar/data/1385849/000106299326001182/exhibit99-2.htm>.
The technical report is effective December 31, 2025. The parent FY2025 filing's
exact incorporated link describes a report dated February 19, 2026; the report's
signature page states February 17. Neither is substituted for publication. A
conservative public-by date of February 26, 2026 comes from the hash-verified
parent filing `RE-EF-10K2025`, SHA256
`c07b98629f07eee431f828d03b4216370375530437cbe8c24f4bf9325ef34d1a`.
The browser copy was created October 22, 2026 at 03:02:17 UTC. Upload receipt and
archive clocks remain separate in `metadata/user_supplied_sources.json`.
Historical byte identity and globally earliest publication remain uncertified.

Admission now requires the complete resolved incorporated URL, not just an
`exhibit99-2.htm` filename. The parent also links a different Sheep Mountain
report with that basename. The adversarial wrong-accession test rejects such a
substitution. All three incorporated technical reports pass the stricter check.
Historical CONNECT failures remain failures; uploads are not HTTP downloads.

## What the source supports

Forty-seven new quoted claims are extracted from the same hash-verified PDFs:
Donald technical engineering/contract statements, the existing Q2 filing's
negative-FID/ownership/development observations, and Vara Mada's comparative
Donald composition. Explicit PDF pages and named numeric cells bind every claim.
They join the existing claim table, now 116 records. Source assumptions, pilot
observations, current reporting, contingent rights and future plans stay distinct.

Table 1.3 (PDF page 28) reports reserve-average HM at 4.5% of bulk ore. Its oxide
figures are **percentages of HM**, not ore: Nd2O3 0.20, Pr6O11 0.056, Dy2O3 0.041,
Tb4O7 0.0064. Minerals/oxides are nested, not additive. Table 15.2 (PDF page 119)
assumes recovery to REEC of 92% for Nd/Pr and 88% for Dy/Tb. These are
mine/concentration planning assumptions, **not White Mesa separation yields**.

For finite declared bulk-ore feed F and one common throughput q, the necessary
partial envelope is `0 <= q <= F; d_e <= q*h*a_e*r_e*phi_e`, where h is HM/ore,
a_e is oxide/HM, r_e is planned recovery to REEC and phi_e is the element/oxide
stoichiometric fraction. The explicit dry-ore normalization is a diagnostic
convention, not a certified available batch. A user cannot feed an HM assay to a
bulk-ore denominator parameter. Omitting h would inflate the coefficients by
about 22.2. Residual contained element remains nonnegative. Other minerals,
chemical inputs, tailings constituents and qualified downstream products are
not fully observed; this is a necessary envelope, not a complete activity.

Sixteen finite-feed LP checks at normalized feed quantities 0, 0.5, 1 and 1,000
exercise finite feed, half-throughput, route closure and owner outage. One common
ore variable constrains all four elements. They match analytical optima and
primal/dual objectives; zero feed/route/owner availability gives zero outputs.
These normalizations remain in **diagnostics**, never empirical stock/supply
records. The 293 Mt reserve is not available inventory, and a planned 30-tonne
product-bin capacity is not opening stock. Design 1,000 dry t/hour multiplied by
7,500 assumed operating hours equals 7.5 million dry t/year; this does not
estimate realized utilization or justify division into four equal quarters.

Table 22.5 (PDF page 187) supplies a **different** financial-model composition:
Nd2O3/Pr6O11/Dy2O3/Tb4O7 = 13.85/3.85/2.67/0.41% of TREO, and 60.6% TREO in
REEC. Conditional composition uses those denominators without a new annual feed
or output estimate. The financial-grade moisture basis is not independently
certified. The separate pit-costing 8% moisture assumption is not silently
applied. Vara Mada Table 19-6 (PDF page 244) lists Donald at
15.90/4.44/2.04/0.36%. The two different disclosed contexts are retained, not
spliced or interpreted as a temporal grade change. Same conservative public-by
date does not prove matched assays or independent measurements.

The reported pilot result (PDF page 93) is 91% **mineral recovery** to REEC and
56% TREO grade; it is not four-element commercial recovery. The confirmatory
92–94% rare-earth phosphate figure (PDF page 94) describes product purity, not
recovery. These observations are not multiplied with an unmatched later assay.
Four rounded ppm-to-oxide source factors agree with formula-specific atomic
weights within the source's four-decimal rounding; this is not assay precision.

## Actual target and ownership observations

Table 22.8 (PDF page 188) planned financing/FID for March 2026. The Q2 filing
(PDF page 22) explicitly states **no FID as of June 30**, and PDF page 62 gives a
new conditional Q3 target. The original target was therefore missed by at least
91 elapsed days through June 30. Its observation enters the information set on
**August 5**, not June 30. Six origin checks enforce that distinction. There is
no actual FID date, completed delay duration, forecast probability, representative
risk spell or population estimate. The new Q3 target is never promoted to an event.

Energy Fuels' reported equity is 9.48% at the report effective date and 12.7% at
June 30; Astron's contemporaneous 87.3% closes to 100%. The conditional 49%
full earn-in differs from both current stakes. One additional source-visible
Donald development snapshot joins the roster without fabricating a state-entry
date or independent risk exposure.

## Routes and unresolved gates

PDF pages 49 and 182 distinguish a planned REEC route via Seattle toward White
Mesa from an HMC coproduct route to China. The REEC offtake takes effect after
FID and may be suspended below its price floor, during which third-party sales
are permitted. A new REEC export licence was being sought at the report date.
The Q2 filing's later assertion that all major regulatory approvals exist is
preserved with its own public clock; it does not independently resolve every
secondary permit or contradict a narrower earlier application by assumption.
No route throughput, operating stock, all-input origin or complete legal control
is inferred. A China-bound coproduct neither proves nor disproves the REEC
chain's eventual independence. Six readiness records keep those gates explicit.

## Data dictionary and reproduction

| File in `data/processed/donald/` | Interpretation |
|---|---|
| `source_claims.csv` | 47 new statements; native value/unit, plan/observation/definition, page, quote, URL/hash and public/copy clocks; subset of the master supplied claim table |
| `nested_material_coefficients.csv` | Four contained-element necessary coefficients; HM/ore, oxide/HM, assumed recovery, input/recovered/residual fractions and claim IDs; stock/output/service missing |
| `conditional_reec_composition.csv` | Four financial-model conditional compositions; oxide/TREO and TREO/REEC bases; no moisture certificate, feed or service |
| `source_numerical_checks.csv` | Four source-rounded stoichiometry checks, one design-rate identity and one reported-equity closure |
| `fid_target_revision.csv` | Initial target interval/public clock, explicit negative-event endpoint/public clock, revised target interval; 91-day lower bound, missing actual event and upper delay |
| `target_vintage_checks.csv` | Six origins; target and negative-observation availability, no admitted event/risk spell |
| `cross_report_composition_versions.csv` | Four disclosed compositional differences and two source hashes; no matched sample or observed-change claim |
| `route_readiness.csv` | Six quoted route/offtake/permit scopes; independent gate verification false, physical route capacity missing |

```bash
uv run python scripts/build_supplied_evidence.py
uv run python scripts/analyze_donald.py
uv run pytest -q tests/test_donald.py tests/test_supplied_evidence.py
uv run python scripts/replicate.py
```

The first focused execution passed **57 tests** across the new and supplied-source
modules. Final full-run counts and host/container reproduction are recorded in
`outputs/diagnostics/final_release_validation.json`; consult that current record
rather than this focused count. `donald_validation.json` and `donald_partial_lp.json`
provide six numerical checks, sixteen LP checks, six origin checks and strict
scientific-label guards. The clearly conditional figure is
`outputs/conditional/donald/material_bases.pdf`; the manuscript uses
`manuscript/donald_materials_table.tex`. Every figure/table is regenerated by code.

The next empirical gate remains dated available feed/stock and full flow bridges,
representative operating assays/recoveries, all processing inputs and origins,
qualified downstream capacities/recipes/routes and consuming-bloc grade demand.
Representative project entry/exit surveillance, four annual public-release clocks,
semiconductor target/access evidence, policy obligations and independent coders,
expert review and a second independent machine remain distinct blockers.
No empirical magnet service, threshold probabilities or new equilibrium is claimed.

## Review repairs

The initial full host pipeline passed 476 tests and 9,304 mixed validation checks; its records are retained in `outputs/diagnostics/donald_pre_review/`. Subsequent source review removed an unjustified wet-basis unit label from the 8% moisture statement; the value remains unchanged and was never used in a conversion. Its native unit is now `percent_moisture_denominator_unspecified`. An adversarial test then found that the partial-LP API would accept manually supplied input fractions totaling 1.2 tonnes per ore tonne even though each element separately lost mass. The real failing test is preserved in `donald_joint_mass_initial_failure.log`. A joint input-mass guard repairs this. No source-derived coefficient changes. The final complete host and container pipelines rerun after the repairs; their current release diagnostics supersede the initial run.

Two further primary-source discovery attempts on October 22 sought a dated
Astron/ASX FID or progress announcement between June 30 and the October 11 freeze:
<https://www.asx.com.au/markets/company/atr> and <https://astronlimited.com.au/>.
Both failed at the configured proxy with CONNECT 403. Exact timestamps/errors are
in `metadata/donald_followup_acquisitions.jsonl`; neither supplied content or
historical observations. A dated actual decision/progress record remains needed;
absence from this repository does not establish that FID never occurred.

## Per-run evidence digests and scientific reproduction

The first disconnected pipeline passed all 477 tests, but the new exact-byte check of `manuscript/claims.json` failed. Its only changed cell was the SHA256 of the saved-game audit; that audit differed only in five `grid_refinement[i].heldout_policy_evaluation.elapsed_seconds` values. Both full audit hashes are valid local provenance and are retained. The initial comparison is archived in `outputs/diagnostics/donald_initial_container_comparison/`.

The repaired comparison keeps 143 registered deterministic artifacts byte identical and separately verifies every claim's exact local evidence hash, claim text/classification/reference identity and all scientific audit fields. Only those explicitly located finite nonnegative performance clocks are excluded from the cross-run scientific JSON comparison. Timings, raw claims and full hashes remain available. Eight adversarial tests reject any changed residual/certificate, changed ordinary evidence, forged hash or invalid clock. No numerical tolerance or acceptance criterion changes. See `src/weaponized/reporting/claim_comparison.py` and the final release certificate for actual executed counts.

## Executed final release

On October 23, 2026 UTC, the repaired full host and network-disabled container pipelines each passed **485 tests with no failures, errors or skips**, **9,304 mixed validation checks** and **2,783 original-source checks**. Host execution took 315.40 seconds; container execution took 355.80 seconds. All 143 registered deterministic artifacts reproduce byte for byte, all 217 compared implementation/configuration/dependency/test files match, and all 43 manuscript claims pass exact local evidence-digest and scientific-content comparison. Both 56-page manuscripts converge and have identical normalized extracted text. The eight curated Donald outputs match their pre-review values. The final release verifier passed every check; see `outputs/diagnostics/final_release_validation.json` and its paired container records.

The tested image is `sha256:c8df7375fdfa1ef71a4bdb3b5646ffd674ee29b5e9c27deccd69598e8824f797`; container `weaponized-donald-claims-final-check` exited zero with network mode `none`. This verifies a clean same-host environment, not an independent second machine. The 25-file original numerical core matches the earlier full recomputation. Nine constant-commitment scenarios and eight fixed-opponent MDP audits were recomputed; the saved large HJB arrays were independently re-audited rather than re-solved. No continuous equilibrium, empirical magnet-service forecast or publication-readiness claim follows.

All eleven original document requests are fulfilled. The remaining source and expert requirements are listed above and in `audit/remaining_requirements.md`; the original files need not be supplied again.
