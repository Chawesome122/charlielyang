# Selected VEU permissions and removal instructions

This extension advances blueprint §§2 and 6.2 with exact recipient, facility, item and exception scope from two already-archived original rules: **2023-22873, 88 FR 71478**, and **2025-16735, 90 FR 42321**. It does not expand the selected 27-phase chronology into a complete current-law database. The original raw XML and metadata hashes remain unchanged. The two existing aggregate chronology rows are retained; the extension adds source-bound detail rather than counting the same instruments as new laws.

## Source-descriptive findings

The October 2023 rule revises two printed VEU entries. Samsung China Semiconductor Co. Ltd has the printed eligible destination at No. 1999, North Xiaohe Road, Xi'an, and an item statement concerning NAND memory. SK hynix Semiconductor (China) Ltd has the printed destination at Lot K7, Wuxi High-tech Zone, Comprehensive Bonded Zone, and an item statement concerning DRAM. Both native scope statements expressly except EUV equipment and the specified specially designed parts, components, software and technology. The exact grammar and complete source strings are preserved; the extract does not certify that every non-EUV item is eligible.

The same rule adds a sentence to §748.15(d) concerning the specified §744.6(c)(2)(i)–(iii), §744.23(a)(1)(iii) and §744.23(a)(2)(iii) restrictions for designated VEUs. The source prints a partial paragraph, including the civil-end-use sentence and asterisks; the extension preserves both the exact paragraph and the instruction **adding a sentence after the first sentence**, so pre-existing text is not silently represented as a newly imposed restriction. The table also expressly says that the supplement does not supersede other EAR provisions, including §748.15(c). These qualifications are material: this extract is not a complete EAR classifier or a blanket authorization for all Chinese facilities or users.

The 2025 original instruction explicitly removes Intel Semiconductor (Dalian) Ltd, Samsung China Semiconductor Co. Ltd and SK hynix Semiconductor (China) Ltd from supplement no. 7 to part 748, effective **December 31, 2025**. Removal of this general-authorization route is not an export prohibition, an observed denied individual license or a quantified access loss. Underlying jurisdiction, other authorizations, individual-license requirements and review standards must still be established for each transaction. No application, shipment, servicing, approval, usable installed stock or functional production is measured here.

Two explicit named-recipient links connect the selected 2023 amendments to the 2025 removal instruction. These links establish the same named parties in the original document pair, not uninterrupted authorization or complete amendment history between them. The selected 2023 rule does not print Intel's prior item/facility scope or the beginning of its authorization; those fields remain missing, rather than being imputed from Samsung or SK hynix. Ownership and domestic/foreign production attribution are not inferred from corporate names.

## Two clocks and source quality

The 2023 rule reports filing **October 13, 2023**, publication/effect **October 17, 2023**. The 2025 rule reports filing **August 29, 2025**, publication **September 2, 2025** and effect **December 31, 2025**: respectively **124** and **120** calendar days of notice before effect. Full FRDOC datelines are preserved. The historical query uses an explicit end-of-day convention without inventing a time zone or certifying globally earliest disclosure. A publication-date sensitivity is separate.

At an August 29, 2025 origin the three removals are source-reported but future-effective; they do not count as already operative. Eleven origin checks straddle both instruments' documentary dates and the freeze. After December 31 the ledger retains the two earlier scope-amendment records alongside the three removal records as historical issued versions. It is never the active-authorized-company set. Present archived-byte checks do not independently certify release-time binaries.

Both 2023 printed citation cells retain `[INSERT PAGE NUMBER]`; the metadata citation does not overwrite them. The source table omits a repeated China country cell in the two amended rows; country context comes from the explicit original amendatory instruction. Native names, facility destinations, item statements and citation strings remain uncorrected.

## Files and executed interfaces

- `codebooks/veu_extension.json`: two original/XML metadata snapshot pairs, **18 exact quote/XPath claims** (14 in 2023; four in 2025) and an explicit named-party crosswalk.
- `src/weaponized/semiconductors/veu_extension.py`: checksum/document/date validation, strict table extraction, literal removal-name checks and `issued_veu_events` with distinct known/effective clocks. Output labels forbid current-law/actual-access interpretation.
- `scripts/build_veu_extension.py`: deterministic offline extraction to `data/processed/veu_extension/`.
- `clauses.csv`: 18 source-bound normalized original quotes, XPath, source role, URL, original and metadata hashes, documentary clocks and retrieval time. Original partial paragraphs and explanatory preamble are explicitly distinguished.
- `issued_events.csv`: two facility/item scope amendments and three explicit removal actions. Native prior Intel scope, actual license outcomes and access/capability scores remain missing.
- `source_clocks.csv`: two documentary records, full filing quotes and separate notice lengths.
- `permission_removal_links.csv`: two exact named-recipient document-pair links, with continuous-authorization/access certification false.
- `origin_phase_checks.csv`: eleven end-of-day source-vintage/phase checks and publication-clock sensitivity.
- `outputs/diagnostics/veu_extension_validation.json`: actual extraction counts, file hashes and scientific-label guards.
- `scripts/analyze_veu_extension.py`: source-descriptive `scope_summary.csv`, `scope_table.tex`, `document_clocks.pdf/png` and `analysis.json` under `outputs/empirical/semiconductors/veu_extension/`.
- `tests/test_veu_extension.py`: real-source golden cells, exact snapshots/quotes, metadata identity/dates/citation, recipient-set/name mutations, substantive source roles, freeze, announced/effective distinction and historical-version retention.

```bash
uv run python scripts/build_veu_extension.py
uv run python scripts/analyze_veu_extension.py
uv run pytest -q tests/test_veu_extension.py
```

Focused test evidence is `outputs/diagnostics/veu_extension_focused_tests.log`. The parent release's full pipeline/container evidence, rather than this local memo, determines integrated release certification. The figure was inspected visually; label placement was adjusted without changing any data.

## Inherited Entity List references remain unresolved

The 111 unprinted Entity List footnote references and 19 unresolved review-policy cells in the earlier selected schedule extract are unchanged. Earlier/later archived note texts do not establish a complete intervening amendment chain, and a later subsection reference must not be borrowed backward. Statutory review provisions and full historical note scope require additional originals and qualified legal review.

Two distinct official statutory-XML routes were actually requested: the eCFR historical §744.3 endpoint for March 2, 2023, and the annual 2023 CFR §744.3 XML on govinfo. Both received CONNECT 403, recorded in `metadata/legal_reference_extension_acquisitions.jsonl`; no statutory text was downloaded or read. A historical endpoint date or annual-edition date would not itself certify first-public availability. No unchanged denied PDF route was retried.

Remaining requirements: obtain the exact historical provisions and all material intervening amendments, adjudicate the 2023/2025 partial-authorizations against the complete EAR and subsequent decisions, establish transaction-specific licenses/shipments/servicing, verify ownership/engineering attribution, and obtain independent legal interpretation/coding. These source claims do not identify the semiconductor domestic state x, foreign availability, causal adaptation or strategic payoffs.
