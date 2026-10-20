# Party-level Entity List schedule review

Research freeze: **2026-10-11**. This continuation resumes a28806a at blueprint §6.2's independent legal-measurement gate. It uses nine existing, hash-verified Federal Register metadata/XML pairs. No new original download succeeded. The earlier term-limited search and scope screen remain unchanged; the original 27-phase chronology is not silently expanded into a complete current-law database.

## What was extracted

All nine additional rules marked `ENTITY_SCOPE_MAPPING_REQUIRED` are included: 2023-04558, 2023-07840, 2023-22536, 2024-10485, 2024-19130, 2024-25411, 2025-00480, 2025-05427 and 2025-17893. Their complete five-column source tables contain **488 destination-specific entry versions** in **1,176 original table rows**, spanning 27 printed destination headings. There are **284 entries under the China heading and 204 under other headings**, including **eight address entries**. The legal China heading also contains Hong Kong addresses; it is preserved rather than replaced with an inferred geographic classification.

A printed entry version is a license-bearing table block in the archived XML, with its attached entity/alias/address continuation cells. It is not a unique company, a distinct newly restricted firm, an approved/rejected license, a transaction or a semiconductor capability observation. The selected rules span multiple sectors and destinations. All aliases and native spellings remain inside their original blocks. Repeated parties across countries or amendments are not automatically merged. The parser rejects changed headers, unknown row layouts, missing country/review/citation cells and orphan continuations instead of guessing.

The five-column order is country, entity, license requirement, license review policy and Federal Register citation. Original XML paths, row ordinals, native cell strings, exact source hashes, URLs, retrieval timestamps and documentary dates bind the records to their originals. The extractor retains **six substantive table notes** and **150 amendatory instructions**, including instructions outside a particular entry's scope. Their existence alone is not a complete legal crosswalk.

## Actual descriptive findings

Across all 488 selected versions, exact review-language categories are **156 presumption of denial; 186 policy of denial; 126 mixed denial/case-by-case; one case-by-case-only; 19 unresolved review cross-references**. Mixed cells retain their food/medicine, telecommunications or other item-specific conditions. The single case-by-case-only entry is Sichuan University in 2023-04558. Rule 2025-05427 contains two presumption-of-denial entries and ten policy-of-denial entries. These observations establish documentary heterogeneity, not approval probabilities, numerical legal severity, access loss, indigenous adaptation or a causal control effect.

Five documents' addition-only instructions cover 248 entries. A **240-row reviewed crosswalk** binds entries in the four mixed documents to their named original amendatory paragraphs and destination contexts. It resolves another 147 additions and 92 revisions. Thus the complete extract has **395 additions, 92 revisions and one provisional addition candidate**. The candidate is Shenzhen NetForward: the instruction says `Microelectronics`, while the table says `Mircroelectronics`. Both strings and the explicit review note are preserved; the name is not corrected or automatically merged. A missing opening quotation mark in the Changzhou NetForward instruction is separately documented; its full literal name is otherwise present in the addition list. All adjudications are by one researcher and require independent legal review. Counts of added entries still include address entries and repeated country entries; no unique new-company count is identified.

## Historical clock contract

`effective_date` is verified against the original effective-date passage and pinned metadata. `publication_date` is the Federal Register publication date. `info_public_date` uses the same original XML's reported official `FRDOC` filing dateline, verified independently of the effective-date passage. Its full printed filing time is retained in `filing_quote`; the code uses an **end-of-day date convention** without inventing a time zone. These documentary records do not certify globally earliest disclosure or independently archived release-time binaries.

Three rules report filing before effect; six publication dates follow effect. A publication-only clock omits **243 entry versions at their effective dates relative to the reported filing datelines**. This comparison is not evidence of actual purchasing anticipation or policy opacity. It also does not justify counting a filed-but-not-effective entry as already operative. `visible_issued_entries` returns only source-visible, effective-by-origin **issued versions**, never a consolidated currently active list. The optional publication-clock sensitivity remains explicit. The initial conservative publication-clock extraction diagnostic is retained; refinement to reported filing dates follows the existing chronology's source-clock convention and leaves all original bytes unchanged.

## Source-quality limitations and failed requests

All **488 citation cells contain unfilled insertion markers**. Authoritative metadata citations are retained for references without replacing those native cell strings. One address contains a rule-date token embedded in the source string (`EaseyNovember 1, 2024`). There is also the instruction/table spelling discrepancy above. These are observable source-format flags, not automatically proved errors in the final paginated law. The parser preserves them. Source identity/hash verification certifies these archived XML contents, not clean transcription of every field in a final published PDF.

**111 entry versions reference table notes not reprinted in their particular amendment.** No later note is silently borrowed to resolve an earlier vintage. A note's absence from this partial amendment does not establish absence of the inherited legal provision, a new exemption or deliberate withholding.

Two exact primary-source links from hashed metadata were requested:

- Public-inspection PDF for 2025-05427: `https://public-inspection.federalregister.gov/2025-05427.pdf?1743005528`.
- Paginated published PDF for 2024-25411: `https://www.govinfo.gov/content/pkg/FR-2024-11-01/pdf/2024-25411.pdf`.

Both failed CONNECT 403. `metadata/entity_schedule_acquisitions.jsonl` preserves the distinct source purposes, discovery hashes and actual failures. No PDF content, correction, newly verified historical binary or separate public-inspection snapshot is claimed. Do not retry an unchanged denied route without a meaningful access change.

The first analysis invocation had a syntax error, retained in `outputs/diagnostics/entity_schedules_initial_analysis_failure.log`; repaired before executing the analysis. The initial environment test selection named nonexistent files and ran zero tests; corrected existing paths then executed 31 passing tests. Neither failure was counted as a passing check. The current integrated run, rather than an earlier partial test log, identifies final validation.

## Data dictionary and reproduction

| File under `data/processed/entity_schedules/` | Unit and key fields |
|---|---|
| `entries.csv` | 488 source entry blocks. Immutable `entry_id`, destination/header XPath, first cell, assembled entity-cell text, original row IDs, literal scope/review/citation, category, footnote references, action evidence and provisional flag. License outcomes, foreign access, domestic capability and causal effects remain null. |
| `source_rows.csv` | Every one of 1,176 original table rows, including decorative rows. Exact XPath/quote/cell JSON, structural role and entry link; no undocumented discarded substantive row. |
| `table_notes.csv` | Six exact numbered notes reprinted in the source tables; no cross-vintage imputation. |
| `amendatory_instructions.csv` | 150 exact original numbered instructions, with paths and provenance; only a validated crosswalk establishes an individual operation. |
| `source_clocks.csv` | Nine pinned document records with effect passage, reported filing stamp, publication metadata and clock differences. |
| `publication_vintage_checks.csv` | Nine before-filing/effect/publication admission checks; no current-law or economic-effect claim. |

`codebooks/entity_schedules.json` pins source hashes, expected entry/row counts, destination coverage and uniform-action rules. `codebooks/entity_entry_actions.csv` contains the 240 mixed-document crosswalk records, exact instruction quotations, entry anchors and explicit adjudication notes. The original-source audit rechecks exact XML paths and independently reparses entry structures, clocks and action evidence from the same verified bytes.

Generated outputs under `outputs/empirical/semiconductors/` are `entity_review_counts.csv`, `entity_source_quality_flags.csv`, `entity_schedule_summary_table.csv`, `entity_schedules_analysis.json`, and PDF/PNG figures `entity_review_policies` and `entity_publication_clocks`. `manuscript/entity_schedules_table.tex` is generated. All are documentary descriptive outputs, physically separate from scenario and synthetic results; the flags do not enter SPOI.

From the repository root:

```bash
uv run python scripts/build_entity_schedules.py
uv run python scripts/analyze_entity_schedules.py
uv run python scripts/audit_original_quotes.py
uv run pytest -q tests/test_entity_schedules.py
```

The default replication DAG runs these builders and the full suite. Actual executed totals and release status are in `outputs/diagnostics/entity_schedules_validation.json`, `original_quote_validation.json`, `pytest.xml` and `final_release_validation.json`.

## Precise remaining requirements

Obtain the paginated originals and contemporaneous public-inspection snapshots; adjudicate the embedded date, insertion markers and Shenzhen spelling difference; obtain blinded independent legal coding; resolve inherited notes against historically correct instruments; consolidate additions, revisions, removals and suspensions through the freeze; resolve aliases/party identities and corporate ownership without treating addresses as firms; map jurisdictions/items/end uses and frozen pre-policy target exposure; and obtain actual approvals, shipments, servicing, installed-stock and qualified manufacturing evidence. None of the new rows identifies the blueprint's foreign-access or domestic-capability states, national payoffs, causal adaptation, empirical magnet service, population hazards or a historical coverage-valid opacity index.
