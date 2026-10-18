# Independent module review and its limits

Parallel reviewers examined modules other than their own. This is computational cross-review within this execution, **not independent human subject-matter certification**.

Executed adversarial tests in `tests/test_independent_audit.py` check late-published training information, persistence recognition/right-censoring, competing-event IPCW scoring, finite opening stock, China-tagged inventory removal, supplier-owned transport failure, project/LP interoperability, nonsmooth policy-knot stability and dense unilateral deviations evaluated directly from saved neighboring values. The latest authoritative test count is in `outputs/diagnostics/pytest.xml`.

Review findings and repairs:

- The stateless physical callback initially returned NaN raw coverage and could reuse a stock if used quarter-by-quarter. It now returns finite defined potential and rejects inventory-bearing inputs; multi-quarter stock conservation remains in the LP.
- A registry key alone did not validate a forecast's training vintage. Input clocks and prediction as-of metadata are now mandatory for scored backtests.
- Central secants at interpolation knots could falsely certify closed-loop stability. Knot roots are now explicitly inconclusive.
- Industrial source review identified four-year Iluka offtake quantities, combined expansion totals, mixed critical-mineral metal capacities, demonstration-campaign tonnage, shared uranium/monazite processing and pre-merger SPAC continuity as material coding hazards. See `docs/rare_earth_evidence_review.md`.
- Original 80-iteration positive fine-grid failures and robust negative-response nonconvergence remain archived. Krylov recovery does not change equilibrium acceptance thresholds.

The independent source review validates what issuers reported, not the engineering truth of every issuer statement. External economics, mineral-processing and semiconductor-control specialists and a second independent machine are still required.
