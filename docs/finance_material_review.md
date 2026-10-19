# Issuer clocks, financing categories and feedstock-dependent plans

Information freeze: **2026-10-11**. Execution: 2026-10-19 UTC. This continuation extracts existing archived issuer reports and their exact-link publication evidence. The additional Iluka presentation request failed; it contributes no text or observation.

## Publication evidence and remaining clock gaps

`src/weaponized/io/publication.py` binds an exact report URL to either its own dated issuer card or a single article's `Article.datePublished` metadata and body link. A date on an adjacent card, another article, a filename, a document signature or a generic WebPage modification date is insufficient. The source PDFs and clock-evidence HTML files have separate SHA256 checks and traceability.

| Report source | Clock evidence | Conservative verified date |
|---|---|---|
| RE-PENSANA-CONSTRUCTION-PDF | RE-PENSANA-CONSTRUCTION; single article with exact PDF link | 2026-01-14 |
| RE-PENSANA-INTERIM-PDF | RE-PENSANA-INTERIM2025; single article with exact PDF link | 2026-03-27 |
| RE-ILUKA-HALF2026 | RE-ILUKA; date inside the exact document link | 2026-08-19 |
| RE-ILUKA-OFFTAKE2026 | RE-ILUKA; date inside the exact document link | 2026-06-23 |

The Pensana interim and Iluka half-year reports previously lacked resolved clocks. The other two dates now have executable exact-link evidence rather than relying on manual fallback. Iluka's offtake **notice is dated June 22**, while the issuer's exact linked card is **June 23**. The bibliography now preserves both dates.

Four annual reports remain unresolved: `RE-ILUKA-ANNUAL2025` and Pensana FY2023/FY2024/FY2025. The featured annual link and company-reports page do not date the individual attachment. A WordPress page's older `datePublished` or later `dateModified` is not an annual report's publication date. Missing dates are not estimated or substituted with signing dates.

`historical_byte_vintage_certified=False`: the dated issuer associations support conservative availability, but no independently archived at-origin web snapshot or original release binary has been certified. Raw archives are immutable; acquisition timestamps, source hashes and the derived public clocks remain distinct. The new data support source-reported descriptive findings with this limitation, not certified historical forecast training or claims of a globally earliest disclosure. The default source loader regenerates the derived clock resolution after rebuilding its raw-source index.

## Actual extracted observations

`codebooks/finance_material.json` specifies **37 claims from three PDFs**. `scripts/build_finance_material.py` checks source and publication-evidence hashes, re-extracts the original PDFs with Poppler, matches exact page-level quotes, validates numerical support and runs the Claim schema. Qualitative disclosures and targets have distinct roles and event kinds.

Pensana's unaudited interim report provides signed July–December reconciliation amounts:

| USD; parentheses in the source are negative | 2024 | 2025 |
|---|---:|---:|
| PPE additions | -4,160,534 | -10,773,620 |
| Saltend intangible additions | -143,570 | -225,102 |
| Total additions | -4,304,104 | -10,998,722 |
| Capital items included in working capital | -65,850 | -4,999,892 |
| Cash payments for PPE/intangibles | -4,369,954 | -15,998,614 |

Both additions identities and both additions-plus-working-capital cash identities reconcile exactly. The positive outflow magnitudes in the figure are explicitly sign transformations, not positive changes in physical capacity. The consolidated payments cannot be assigned entirely to Longonjo or interpreted causally. The 2024 comparatives retain their March 2026 source vintage.

Contracted capital commitments are a separate stock of obligations: USD 22,303,840 at December 31 versus USD 2,502,588 at June 30, 2025, primarily relating to Longonjo. The proposed USD 165 million Cascade transaction remained subject to long-form documentation and share applications in the March report. The going-concern disclosure depended on additional funding. Neither is coded as fully received financing or a completed ownership change.

The same report describes main Longonjo construction commencing in July 2025, adding one interval-dated C-state observation (`IND-009`) with a March 27, 2026 source-public clock. This is not retroactively available at earlier forecast origins and does not establish a full first-exit protocol. The roster now contains **61 records, 24 projects and 32 activities**; 29 adjacent pairs still do not supply admissible first-exit spells.

Iluka's half-year report explicitly states AUD as its default currency. The base EFA facility is AUD 1,650 million, with reported drawn/undrawn balances of 897.5/752.5 million at June 30, 2026 and 609.7/1,040.3 million at December 31, 2025. Both reported rounded-balance identities reconcile exactly. A separate AUD 75 million overrun allowance was undrawn. Offtake satisfied an access condition, but additional funding retained a draw-sequence condition after initial arrangements were fully used. Prior undrawn arithmetic does not establish that unrestricted draw eligibility existed then.

Eneabba PPE additions of AUD 236.7 million in H1 2026 (260.7 million comparative) include capitalised interest and accruals. They are not the change in borrowings or cash payments. Eneabba's AUD 447.9 million commitments are a subset of group commitments of AUD 463.4 million, not additive. All finance quantities remain inputs, balances, obligations or conditions; no physical output, project-financing completion probability or causal response is inferred.

Pensana's reported reserve of 139,000 tonnes contained NdPr oxide and 3.04% TREO ore grade retain their geological classification. The grade is not NdPr grade. A reserve is not extracted annual feed or available opening inventory; no division by mine life, assumed recovery or elemental split is performed.

## Product plans and contract terms

Iluka's June notice gives prospective stockpile-only figures of approximately 3,500 tonnes NdPr and 170 tonnes combined DyTb. The additional-feedstock figures are 5,500 and 750, subject to assemblage. Ratios on a commensurate same-product basis are approximately **63.6% and 22.7%**, respectively. The quoted footnote does not explicitly supply an annual denominator, so none is inserted. These ratios do not identify recovered element flows, inventory amounts, Chinese-input origin, annual output, N-1 robustness, demand coverage or game-state y. Combined DyTb is not split.

The 1,200-tonne oxide offtake covers an initial four-year term beginning in 2028. Its footnote specifies take-or-pay for **90% of the material volume**. The USD 155 million minimum-price revenue statement is conditional on product sales; it is not received cash or an unconditional sovereign payoff. The unnamed customer and confidential individual prices do not supply final magnet recipes, demand weights or contractual route capacities. Private issuer confidentiality is not a Chinese policy-opacity score.

## Files, roles and reproduction

Tables under `data/processed/finance_material/`:

| File | Interpretation |
|---|---|
| `publication_clock_audit.csv` | Report and clock-source IDs/hashes/URLs; exact-link method/support; resolved date or explicit unresolved reason; historical-byte-vintage limitation. |
| `observations.csv` | Claim/version IDs; native quantity, unit, product, financial role, sign, period/event kind; PDF page/quote; report and public-clock provenance; interpretation. |
| `prospective_product_comparisons.csv` | Separate same-product base/expanded quantities and ratios; annual output, China-free service and Dy/Tb split remain unidentified. |

Figures: `outputs/empirical/rare_earths/project_finance_categories.pdf` and `eneabba_feedstock_comparison.pdf`. Diagnostics: `outputs/diagnostics/publication_clock_validation.json` and `finance_material_validation.json`. The global source registry preserves acquisition-date metadata alongside derived clock evidence; the claim trace includes both report and publication-evidence hashes.

Run `scripts/resolve_publication_clocks.py` after `scripts/build_rare_earths.py`, then `scripts/build_finance_material.py`. The default replication includes both, the dated construction observation, validation, tests, figures and manuscript. Tests in `tests/test_publication_finance.py` reject unrelated/modified-page clocks, incompatible products/units, invalid balances and confusion between additional credit and base facilities.

## Exact blockers

The new acquisition attempt targeted `https://www.iluka.com/media/1b5ptzh4/2026-half-year-results-presentation.pdf`, whose exact issuer card is dated August 19, 2026. It failed with CONNECT 403; `metadata/finance_material_acquisitions.jsonl` preserves the operation. No contents are attributed to it.

Obtain the unresolved annual-report release records and independently archived source vintages; review the complete financing and offtake contracts where lawfully public; verify closing, disbursement, ownership, commissioning, assays, recoveries, qualified rates, routes and final-grade demand. Inclusive project eligibility and first-exit surveillance remain absent. These financial observations and plans do not authorize population hazards, real-world service probabilities, a causal restriction effect or payoff identification.
