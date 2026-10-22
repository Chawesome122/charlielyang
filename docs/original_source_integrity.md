This memo records the 335-check engineering/legal checkpoint. The subsequent [White Mesa review](white_mesa_review.md) adds 49 claims; the current audit checks 384 records across ten tables and 34 originals. All scope limitations below remain applicable.

# Original-byte evidence and reproducible extraction

Freeze: **2026-10-11**. The continuation found that some legacy builders verified the original's hash but then consumed a separately editable `.extracted.txt` or `data/interim/` text aid. This could let an altered derivative supply a claim without changing the checked original. No corrupted research observation was discovered; this was a trust-chain weakness.

`src/weaponized/io/original_text.py` now reads one immutable byte snapshot, checks its SHA256 and extracts that same snapshot. PDFs are passed to Poppler on standard input; HTML is parsed from the verified bytes. The cache is keyed by bytes and document form, and each public access rechecks the current original. Changing a path during extraction cannot substitute different input bytes. A later access with the old digest rejects a changed original.

The additional rare-earth PDF builder, Lynas histories/revisions, project histories, project discovery, industrial evidence, IEA body extraction and semiconductor legal/financial builders now use originals directly. Issued legal XML retains its document-identity parser and original checksum verification. Text aids remain reading conveniences. The change does not alter the LP, transition model, differential equations or game primitives.

`scripts/audit_original_quotes.py` independently rechecks **335** existing quote/table records across **nine tables and 33 original sources**. These include duplicate claims in the merged roster; the count is not 335 independent observations. It enforces `pdf_page` and anchored `PDF page N` locators, rejects conflicting or invalid page specifications, and reparses the quarterly table's source header, dates, units, products and cells. Thirty-three explicit PDF-page locations in the industrial/merged tables received additional reviewer checks. The original quote check is separate from independent measurement of production, engineering feasibility or economic effects.

The audit's scope is present archived original-byte support. Its output does **not** certify release-time web/PDF/XML bytes, globally earliest public dates, legally complete current law, independent issuer verification, a population risk set or industrial service. The separate publication extension records those limitations and actual two-clock exclusions.

Executed evidence:

- `data/processed/source_integrity/original_quote_audit.csv`
- `outputs/diagnostics/original_quote_validation.json`
- `tests/test_original_text.py` and `tests/test_original_text_review.py`
- The expanded default pipeline's exact command exits and logs.

Tests exercise poisoned text aids, path replacement during PDF extraction, corrupted originals after a cache hit, incorrect digests, hidden script content, failed Poppler extraction, explicit page conflicts and empty/invalid locators. The integrated release tests and disconnected-container evidence, rather than this memo alone, identify the final tested code version.

The MP measurement continuation expands original-source coverage to 577 checks across 12 tables and the same 34 originals: 174 native MP cells are re-parsed with named headers/rows, tokens, values, units, missing states and public clocks; 19 definition quotes are also verified. Exact executed current counts are in `outputs/diagnostics/original_quote_validation.json`. It does not independently certify release-time source bytes or industrial measurements.

The SMIC operating continuation adds 120 named PDF cells, twelve definition quotes and four page-1 issuer datelines. The current original-source audit covers 713 checks across 15 tables / 38 originals, with page-specific reparsing and explicit quarter headers. It certifies present archived-byte support, not independent production truth or historical release-byte certification. Exact diagnostics are in `outputs/diagnostics/original_quote_validation.json`.

The party-schedule continuation adds original XML row/note/instruction/date verification and full entry/action re-extraction for all nine selected additional Entity List rules. The audit checks the same checksum-verified snapshots, explicit XML paths, exact legal review text, country/continuation structure and documentary clocks. Native citation insertion markers and spelling/date anomalies remain preserved. Exact current counts are in `outputs/diagnostics/original_quote_validation.json`; the extension does not certify clean published-PDF transcription, historical binaries or complete current law.

The operating-origin/VEU continuation adds 33 original commercial-disclosure quotes and 18 exact issued-XML/XPath passages. The standalone expanded audit passes 2,602 checks across 22 tables and 49 original sources, with both new legal originals already archived but newly covered by quote auditing. MP quotations are re-extracted from the same verified HTML bytes; VEU operative clauses, explicitly explanatory content and documentary clocks preserve distinct roles. Independent internal computational reviews additionally use standard-library HTML/XML parsers and original SEC submission records. These reviews do not supply external specialist certification, global earliest disclosure or historical byte identity. The final integrated release report identifies the exact tested version and current counts.
