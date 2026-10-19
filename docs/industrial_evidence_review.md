# Downstream evidence and legal-source continuation

This memo describes the earlier 55-record checkpoint. The subsequent [project-history review](project_history_review.md) adds five history records (60 total), preserves Upton timing revisions and audits source-observation protocols.

Freeze: 2026-10-11. Execution: 2026-10-18. New observations in this continuation are extracted from already archived, pre-freeze issuer filings and original Federal Register XML. Eight new issuer-site requests all failed at the proxy with CONNECT 403; `metadata/rare_earth_expansion_acquisitions.jsonl` preserves those failures. No observation is attributed to an unsuccessful request.

## Industrial findings and measurement limits

`codebooks/industrial_evidence.json` contains eight project-milestone specifications and five technical claims. `scripts/build_industrial_evidence.py` verifies source bytes, public dates, exact quoted passages and numerical support. Sources are the USA Rare Earth and Energy Fuels FY2025 Forms 10-K and Lynas FY2025/FY2026 annual reports. Output keys preserve the distinction between operator, prospective-acquirer and supply/processing-counterparty statements.

- Lacq: 3,750 metric tonnes/year is a planned metal/alloy facility, separate from UK operations. Stillwater's planned metal stage does not inherit its magnet-stage commissioning.
- Caremag: the USA Rare Earth filing provides a counterparty's commissioning target, not independently verified construction or operation.
- Korean Metals Plant: Energy Fuels describes reported metal/alloy production by ASM's plant; its proposed acquisition is conditional in that source. Neither a completed ownership change nor independently measured qualified throughput is inferred.
- JS Link Kuantan: the FY2025 non-binding MoU and FY2026 partnership are versions of one activity. The latter explicitly states prospective annual 3,000-tonne magnet capacity. They are not two plants or proof of stable output.
- LS Eco Energy Vietnam: a framework and convertible instruments are not an operating plant, project FID, fully financed construction, or a quantified tolling route.

The Energy Fuels filing reports approximately 1.2 tonnes of NdPr oxide processed into 3.0 tonnes of automotive-qualified permanent magnets by an unnamed Korean counterparty. It identifies Florida/Georgia monazite as the oxide feed origin and refers to an announcement on September 9, 2025. The archived source's verified public clock is February 26, 2026. The claimed earlier announcement date is not substituted as a verified source vintage. The counterparty is not equated with ASM KMP, and the separate 45H block-grade statement is not independently linked to the quantified batch.

The product-mass ratio is approximately 2.5 magnet tonnes per oxide tonne, **not** elemental recovery. Aggregate mass conservation, conditional on reported masses and nonnegative other outputs, gives a necessary lower bound of approximately 1.8 tonnes of additional inputs. Unknown inputs include non-REE constituents, potentially other rare earths and process materials; their amounts/origins and the process outflows are unmeasured. This is an accounting bound, not an inferred recipe or a feasible future supply schedule. The consumed historical batch is not future opening stock. No annual rate, utilization, sustained qualified throughput, China-free service or forecast probability is estimated.

The combined roster has 55 records, 24 projects and 32 activities. It remains selected and lacks representative entries/exits and failure discovery. Source-backed status snapshots are not transition durations or population hazard observations.

## Coverage audit and dictionaries

`scripts/build_evidence_coverage.py` verifies all roster-source hashes and produces per-activity flags and stage-level attrition counts. Within this selected roster, 31 activities have a verified public-source clock, 12 a native capacity mention, 11 an annual native capacity mention and one a total campaign limit. Complete element recipes, finite route capacities, independently verified stable qualified rates and matched final demand have zero **verified documentation records** here. These zeros do not mean zero real industrial capacity or deliberate opacity.

| Output under `data/processed/industrial_evidence/` | Key fields and interpretation |
|---|---|
| `project_milestones.csv` | Stable record/project/activity IDs; state, stage, country; source role; native capacity/unit; event interval; conservative public clock; quote, locator, hash. Planned capacity is not delivered service. |
| `technical_claims.csv` | Claim-schema observation/version IDs; quantity or categorical value, native product/unit, validity/public dates and source. Approximate finite-batch values, purity and grade remain different measurement objects. |
| `activity_coverage.csv` | Latest eligible source snapshot per activity, including undated discovery candidates flagged ineligible; documentation flags, not manufacturing outcomes. Campaign totals are never annualized. |

`outputs/empirical/rare_earths/finite_batch_evidence.json` records the conditional arithmetic and exact remaining inputs. `evidence_coverage_by_stage.csv` and `evidence_coverage.pdf` report counts, not physical capacity.

## Additional legal review

The 41 additional archived issued texts are manually scope-screened in `codebooks/legal_discovery_screening.csv`, then verified against original XML identity, bytes, quoted language and source-public clocks by `scripts/review_legal_discovery.py`. Counts: eight procedural; nine other-destination/enforcement; nine unresolved entity mappings; six unresolved cross-cutting item rules; five import/domestic context; four admitted document sources.

Four originals add five reviewed phases: specified YMTC-related listings effective 2022-12-16; Biren/Moore Thread-related listings effective 2023-10-17; the 3A090.a correcting amendment effective/filed 2025-02-11 but published 2025-02-14; and separate approved/unapproved UAE advanced-computing scopes effective/filed 2026-07-10 but published 2026-07-14. Exact effective-date support is separately checked. The original December 2023 document 2023-27588 only extends the comment period despite mentioning updates and corrections in its title. It is not a new export restriction.

The chronology now has 27 phases and 21 reviewed U.S. original documents. The two discovery queries still identify 58 candidates; 37 are outside the selected event corpus. Screening is not item-level consolidation or independent legal review. Presumptions of denial remain license requirements, UAE exceptions do not imply China access, proposed rules remain prospective, and no numerical access loss, capability score or causal effect is inferred.

## Archived financial-input extension and exact acquisition blockers

`scripts/build_mp_investment.py` extracts the USD `PaymentsToAcquirePropertyPlantAndEquipment` facts from the already archived SEC company-facts source `RE-MP-FACTS`. The 53 retained filing versions describe 28 distinct reported durations, not 53 independent observations. `mp_cash_ppe_versions.csv` preserves array locators, accession numbers, filing clocks, period starts/ends, nominal amounts and source hashes; `mp_cash_ppe_asof_freeze.csv` selects the latest admissible version for each duration. Pre-2021 combination/predecessor periods and post-freeze filings are excluded. Report fiscal-year metadata do not replace the actual observation dates. Quarter, half-year, nine-month and annual cash flows overlap and must not be summed indiscriminately.

The six January–June cash-PPE totals are USD 44.691, 122.584, 130.236, 98.326, 59.473 and 307.711 million for 2021–2026 respectively. For each of 2024–2026 the available first and second quarters sum exactly to the half-year total; 2026 gives 77.376 + 230.335 = 307.711 million. Earlier years lack both separately reported quarter tags. These are consolidated nominal investment inputs: no project allocation, price adjustment, physical output, policy causal response or gain in game-state resilience is inferred. The figure is `outputs/empirical/rare_earths/mp_halfyear_cash_ppe.pdf`; the extraction/reconciliation evidence is `outputs/diagnostics/mp_investment_validation.json`.

The following latest Q2 2026 filings were identified in archived SEC submission metadata. Direct requests to their official SEC filing URLs failed at the proxy with CONNECT 403; their texts have **not** been read. Exact attempts are appended to `metadata/rare_earth_acquisitions.jsonl`.

| Issuer (CIK) | Filing public date | Accession | Primary document |
|---|---|---|---|
| MP Materials (1801368) | 2026-08-07 | `0001801368-26-000048` | `mp-20260630.htm` |
| Energy Fuels (1385849) | 2026-08-05 | `0001385849-26-000029` | `efr-20260630.htm` |
| USA Rare Earth (1970622) | 2026-08-10 | `0001970622-26-000057` | `usar-20260630.htm` |

Recover those original filings next to review industrial updates and reconcile the MP tags against original XBRL contexts. The archived company-facts representation is a distinct admissible financial-data source; it does not substitute for reading the unavailable narrative or resolving subsequent commissioning/ownership evidence.
