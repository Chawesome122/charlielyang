# Missing issuer clocks and actual vintage exclusion audit

Information freeze: **2026-10-11**. This audit continues the existing exact-link clock work. It resolves **zero additional public dates** and certifies **zero historical source-byte vintages**. Four annual reports remain excluded from in-freeze source-vintage analysis until a verifiable release association is obtained.

## Executed source search and exact blockers

The archived Pensana company-reports page links the exact FY2023, FY2024 and FY2025 PDFs, but none has its own report-specific public date. Its `WebPage.datePublished` is August 17, 2020 and `dateModified` is October 15, 2025. These dates concern the reports page, not the individual attachments. The Iluka homepage contains an undated exact link to its 2025 annual report. Its neighboring dated half-year and release cards do not date that annual report.

The Pensana report list contains a separate download-arrow control alongside each of its 2023–25 annual-report titles. All three arrows link to `Pensana-AR-2023.pdf`, whereas the actual titles link to distinct FY2025, FY2024 and FY2023_FINAL binaries. The audit records these off-target controls. It neither downloads an assumed alias nor treats these distinct URLs as identical source versions. The generic arrow must not be used to silently obtain the wrong report.

Three new official URLs were attempted once through the environment's configured network route:

- `https://pensana.co.uk/lse-announcements/`
- `https://www.iluka.com/investors-media/financial-results/`
- `https://www.iluka.com/investors-media/asx-releases/`

All three failed with `Tunnel connection failed: 403 Forbidden`. Exact operations and retrieval timestamps are in `metadata/publication_extension_acquisitions.jsonl`. No contents or release dates are attributed to those inaccessible resources. No previous failed URL was retried or access restriction bypassed.

## Executed integrity and admissibility checks

`scripts/build_publication_extension.py` separately verifies report-PDF and issuer-HTML hashes, re-executes all eight existing exact-link clock rules, and records a **48-row source/origin matrix**: eight reports at six declared origins. Known issuer-stated public availability, missing publication date, archive-retrieval timing, and independently certified original-at-vintage bytes remain distinct dimensions. The four known dates support conservative issuer-stated availability; they are neither globally earliest release certificates nor independent proof that currently archived binary contents match the original release. All eight downloads occurred after the October 11 information freeze, and this extension adds no independent historical snapshot certificate.

An **18-row rejected-date-candidate table** records the four PDFs' creation/modification metadata, the three Pensana attachments' generic reports-page dates, and all four filename/upload paths. These metadata are retained for diagnosis and never substituted for publication. PDF authoring dates can differ from distribution dates, and upload directories and document signatures do not prove public accessibility.

The audit also applies the existing two-clock selectors to the **37 actual finance/material claim versions**, without adding data or estimates:

| Origin | Claim versions available by the issuer clock | Event-date-only claims that would leak later information |
|---|---:|---:|
| 2024-12-31 | 0 | 5 |
| 2025-12-31 | 0 | 15 |
| 2026-03-31 | 17 | 3 |
| 2026-06-30 | 25 | 12 |
| 2026-09-30 | 37 | 0 |
| 2026-10-11 | 37 | 0 |

For example, the 2024/2025 comparative financial quantities read in the March and August 2026 reports cannot enter a December 2025 forecast merely because their reporting periods end by then. By June 30, 2026, twelve retrospectively dated claim versions in the August Iluka report remain unavailable. These are engineering checks on this selected extraction, not population disclosure-lag estimates, uncertainty intervals, forecasting skill or measured strategic opacity. Available information includes announcements according to their event labels; passing an information clock does not establish completed physical output or source-byte certification.

## Files and reproduction

Run after `scripts/resolve_publication_clocks.py` and `scripts/build_finance_material.py`:

```bash
.venv/bin/python scripts/build_publication_extension.py
.venv/bin/pytest -q tests/test_publication_extension.py
```

Outputs under `data/processed/publication_extension/` are `annual_clock_blockers.csv`, `rejected_date_candidates.csv`, `source_origin_readiness.csv`, and `claim_origin_masking.csv`. Executed diagnostic: `outputs/diagnostics/publication_extension_validation.json`. The codebook declares origins and the unresolved annual-report universe. All 12 targeted tests passed, including wrong-report controls, exact-day masks, UTC retrieval comparisons, missing dates and freeze rejection.

Required next evidence is a report-specific issuer/exchange release record for each annual report, plus independently archived release-time HTML/PDF versions or other lawful source-version evidence. Source-original quotation verification is a separate integrity check and does not certify public availability. No empirical hazard, service forecast, causal effect or historical SPOI is enabled by this audit.
