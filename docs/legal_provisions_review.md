# Selected semiconductor provisions: original-rule extraction

Research freeze: **2026-10-11 inclusive**. This continuation uses already archived Federal Register originals. It makes no new network acquisition and does not replace the 27-phase event chronology with a purported consolidated legal regime.

The executed extract contains **41 claims**, **65 exact operative XML elements**, **three exact DATES elements**, **24 structured numerical bounds**, and **four verified parameter-restatement links**. Six original XML/metadata files are checked against both their acquisition manifest and the exact hashes fixed in the review codebook. A changed source, locator, quote, document identity, instruction number or unsupported threshold sign causes extraction to fail. Technical validation binds each bound to its named source quantity and registered native-unit basis; a nearby number attached to another parameter is rejected.

These are primary legal-text observations. They are not observed license decisions, foreign-access scores, indigenous-capability scores, technological targets, causal estimates or national utility parameters. Legal interpretation has one research coder; qualified legal review and blinded second coding remain outstanding.

## Sources and clocks

| Original issued rule | Citation | FR publication / conservative public clock | Legal effect | Selected compliance treatment | Claims |
|---|---|---|---|---|---:|
| [2023-23055](https://www.federalregister.gov/documents/2023/10/25/2023-23055/implementation-of-additional-export-controls-certain-advanced-computing-items-supercomputer-and) | 88 FR 73458 | 2023-10-25 | 2023-11-17 | Selected CCL instruction 38: 2023-11-17 | 8 |
| [2024-28270](https://www.federalregister.gov/documents/2024/12/05/2024-28270/foreign-produced-direct-product-rule-additions-and-refinements-to-controls-for-advanced-computing) | 89 FR 96790 | 2024-12-05 | 2024-12-02 | Selected instructions 16 and 31: 2024-12-31; selected instructions 11 and 13 default to effect date | 17 |
| [2026-00789](https://www.federalregister.gov/documents/2026/01/15/2026-00789/revision-to-license-review-policy-for-advanced-computing-commodities) | 91 FR 1684 | 2026-01-15 | 2026-01-15 | Selected instructions 2, 4 and 7: effect date | 16 |

The December 2024 rule explicitly permits legal effect to precede Federal Register publication and specifies delayed compliance for an enumerated list of instructions. The extract does not backdate public knowledge to effect, a press-release date, an assumed public-inspection date or the date an archived endpoint was retrieved. Its `info_public_date` is a conservative source-supported publication clock; `earliest_public_date` is missing and `first_public_date_certified` is false. Original-at-publication XML bytes are not independently certified.

The HBM exception text in instruction 13 follows the rule's default timing; classification and the selected license/review amendments in instructions 31/16 have December 31 compliance. This difference does not establish actual shipments, earlier applicability of every underlying obligation or approval of any transaction.

## Verified item-level observations

The selected 2023 ECCN 3A090 branches specify the following alternatives for an integrated circuit with one or more digital processing units. The associated exclusions and definitions must still be applied.

| Branch | Exact numerical conjunction |
|---|---|
| 3A090.a.1 | TPP ≥ 4,800 |
| 3A090.a.2 | TPP ≥ 1,600 and performance density ≥ 5.92 |
| 3A090.b.1 | 2,400 ≤ TPP < 4,800 and 1.6 ≤ performance density < 5.92 |
| 3A090.b.2 | TPP ≥ 1,600 and 3.2 ≤ performance density < 5.92 |

The selected original December 2024 paragraphs restate all four numerical conjunctions. The four links in `amendment_links.csv` certify only that parameter comparison. They do not establish unchanged complete scope, independently reviewed intervening amendments or full-instrument supersession.

The 2023 TPP definition is `2 × MacTOPS × operation bit length`, aggregated over the processing units. Associated technical notes specify theoretical peak operations, the prescribed operation bit length and dense rather than sparse matrix performance. Performance density divides TPP by applicable non-planar logic-die area. These are not interchangeable with the HBM package/stack-area denominator. The non-datacenter exclusion requires both the specified design/marketing condition and TPP below 4,800. A generic non-datacenter label is insufficient.

The December 2024 extract verifies these separate HBM rules:

- ECCN **3A090.c** uses memory bandwidth density **strictly greater than 2 GB/s/mm²**. Its technical note defines package/stack area, includes the stated DRAM scope and control-interface/PHY case, and excludes processing-dominant logic/HBM co-packages from this particular category. That exclusion does not establish that the co-package escapes other controls.
- Section **742.6(a)(6)(i)(B)** requires licenses for the specified HBM commodities, related software and technology to or within Macau or Country Group D:5, with its explicit deemed-export/reexport exclusion. A required license is not an absolute prohibition.
- Section **742.6(b)(10)(ii)** distinguishes approval and denial presumptions by the specified headquarters/ultimate-parent conditions. No license application or decision is observed in this extract.
- HBM category c is ineligible for NAC/ACA under the selected section 740.2 note. The same note makes its specified NLR route conditional on no applicable parts 744/746 license requirements.
- Section **740.25** has its own density condition **strictly below 3.3 GB/s/mm²**, eligible exporter/headquarters conditions, direct-purchase and packaging-site routing, documentation and return-shipment conditions, finished-product limits, exceptions for the stated TGL proviso, excluded routes and discrepancy reporting. The discrepancy trigger is **greater than 1 percent**; an unresolved discrepancy must be reported within the stated **60 days**. The full quoted requirements are retained in `quoted_elements.csv`.

Thus a hypothetical density between 2 and 3.3 can satisfy both selected numerical screens while still failing other conditions. At density exactly 2, the quoted classification bound fails. At exactly 3.3, the quoted exception bound fails. The software reports only the parameter-screen result and explicitly leaves legal eligibility, license approval and foreign access undetermined.

The January 2026 rule introduces conditional case-by-case review for specified **exports from the United States** to end users in China/Macau with **TPP <21,000 AND total DRAM bandwidth <6,500 GB/s**. The exact operative paragraph retains denial presumptions for its other specified applications. It does not automatically extend the path to reexports or in-country transfers, issue a license, or amend the separately quoted HBM review paragraph.

All nine certification conditions are preserved: prior U.S. shipments and product specifications; sufficient U.S. supply and foundry-capacity protection; the specified **50-percent aggregate-TPP comparison**; excluded end uses/users and transaction parties; KYC procedures; remote-user disclosure; IaaS conditions; physical security; and testing of every shipment. The 50-percent rule is a product-specific comparison against specified cumulative U.S. shipments, not a fraction of global chip capacity. The extract also retains the total-DRAM-bandwidth definition, including co-packaged HBM and other DRAM, the interconnect double-counting restriction, all three independent laboratory qualifications, pre-export laboratory certification, and the stated laboratory-revocation consequence. These duties are not evidence that applicants actually complied.

## Files, schema and integration contract

The new implementation is disjoint from the older chronology:

- `codebooks/legal_provisions.json`: fixed original hashes, exact normalized XML quotes/XPaths, reviewed instruction numbers, clock treatment, item-level interpretation, numerical bounds and explicit missing scores.
- `src/weaponized/semiconductors/provisions.py`: exact original-clause validation, separate clock checks, issuance-phase visibility and conservative numerical parameter screens. `issued_clause_phases` retains old originals and does not consolidate current law.
- `scripts/build_legal_provisions.py`: offline rebuild from immutable raw sources. It does not read `.extracted.txt` aids or a live EAR endpoint.
- `data/processed/legal_provisions/provisions.csv`: 41 claims with both source/metadata hashes, URLs, original citation, retrieval and publication clocks, effect, compliance, instruction, product codes, scope and interpretation. The 2026 review cross-reference is retained rather than inventing a fully consolidated upstream ECCN list. `severity_ordinal` and `physical_access_loss` are missing; `current_law_consolidation_certified` and `approval_observed` are false.
- `quoted_elements.csv`: 65 exact paragraph quotes, stable original XML locators, original artifact SHA256 and normalized quote SHA256.
- `technical_bounds.csv`: 24 branch-level conjunction bounds with native units and strict/non-strict operators. Different branch IDs remain alternatives; this table is not a complete classifier.
- `amendment_links.csv`: four parameter-only restatement links, explicitly not full supersessions.
- `issued_phase_checks.csv`: source-visible selected issuance phases at nine historical origins, including publication/effect/compliance boundary cases. These are mechanical checks of dated source records, not an empirical legal treatment series.
- `outputs/diagnostics/legal_provisions_validation.json`: executed counts, source/clock limits, explicit consolidation gaps and hashes of all five CSVs.
- `tests/test_legal_provisions.py`: 20 executed checks, including original document/quote identity, cutoff and deferred compliance, strict/inclusive boundaries, missing inputs, all nine certification conditions, and missing access/current-law claims.

Add `build_legal_provisions.py` to the default pipeline after `run_semiconductors.py` and before report generation. It uses the existing `metadata/semiconductor_sources.csv`; no new source IDs or downloads need to be registered. Add its five CSVs to container byte-comparison outputs. For claim traceability, join each `claim_id` to its `source_id`/`source_sha256`, its `metadata_source_id`/`metadata_sha256`, and all rows of `quoted_elements.csv` for exact locators. The codebook additionally fixes each reviewed original SHA256.

Executed commands:

```bash
.venv/bin/python scripts/build_legal_provisions.py
.venv/bin/pytest -q tests/test_legal_provisions.py
.venv/bin/pytest -q tests/test_legal_provisions.py tests/test_legal_provisions_review.py
```

The focused suite contains **20 tests**. Together with five independent source-semantic review tests, **25 tests passed** after the robustness repair. Three mutation cases run the actual builder with swapped parameter names, values or native units and verify failure before any output is written. The correct five derived CSV hashes remained unchanged. These statements do not claim a full-project or disconnected-container run; the parent continuation integrates and executes those separately.

## Exact unresolved consolidation and empirical requirements

1. Read and reconcile all effective intervening amendments, corrections, rescissions, suspensions, enforcement announcements and country-group changes through the freeze, with the transaction-specific destination/user scope. The archived April 2024 clarification and January 2025 instruments are not silently assumed to be incorporated here.
2. Resolve complete EAR jurisdiction, de minimis/FDP, Entity List, end-use/end-user and parts 744/746 conditions. This extract does not cover all conditions under NAC/ACA, TGL or other license exceptions and does not create a complete maintenance or services rulebook.
3. Certify first-public-inspection dates and original-at-vintage source bytes before using them as the earliest treatment/anticipation clocks.
4. Obtain qualified independent legal interpretation and blinded second coding. Exact text matching does not itself validate the single-coder interpretation.
5. Obtain transaction-level license applications/approvals, usable shipments, supplier service access and qualified target-specific engineering evidence. The 27 chronology phases and 41 new clause claims cannot identify immediate access loss, delayed substitution or a legal-severity-to-physical-loss coefficient by themselves.
6. Preserve missing technical target and domestic/foreign/combined availability scores. Neither a strict technical bound nor an approval/denial presumption identifies the amount of functioning production available to China.

The item-by-item legal acceptance requirement therefore remains **PARTIAL**. No current-law or causal semiconductor finding is certified by this extension.
