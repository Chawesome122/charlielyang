# Source-reported concentrate engineering constraints

Information freeze: **2026-10-11**. This continuation reuses two archived MP Materials Forms 10-K, freshly verifies each original HTML checksum and parses those original bytes rather than a derived text aid. No download, operating assay, expert process certification or new inventory measurement is claimed.

## Evidence and substantive findings

`codebooks/engineering_inputs.json` contains **32 claims: 28 numerical and four categorical**. The sources are `RE-MP-10K2024`, publicly filed February 28, 2025, and `RE-MP-10K2025`, publicly filed February 26, 2026. Original links:

- [FY2024 Form 10-K](https://www.sec.gov/Archives/edgar/data/1801368/000180136825000009/mp-20241231.htm)
- [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1801368/000180136826000008/mp-20251231.htm)

The source-public clocks are conservative archived filing availability. They do not certify independently archived original-at-vintage binaries. Retrieval dates, SHA256 values, reporting dates and public dates remain separate. `valid_date` is the annual reporting-period end; it does not assert the date when an engineering assumption was first adopted.

Both reports state average concentrate composition, conditional on its total rare-earth oxide (TREO) content: **15.7% PrNd, 1.8% SEG+, 32.3% lanthanum and 50.2% cerium**. These sum to 100%. They are joint shares of one feed, not four independently available full-capacity streams. They are not percentages of bulk ore or bulk concentrate. In their pit-optimization notes, the reports assume concentrate containing **60% TREO**.

The recovery assumptions differ by geological/economic model context:

| Separation product; source-native recovery % | FY2024 resource | FY2024 reserve | FY2025 resource | FY2025 reserve |
|---|---:|---:|---:|---:|
| PrNd oxide | 89.7 | 89.7 | 89.7 | 89.7 |
| SEG+ precipitate | 97.9 | 97.9 | 97.9 | 97.9 |
| La carbonate | 75.0 | 75.0 | 75.0 | 74.9 |
| Ce chloride | 11.5 | 11.5 | 11.5 | 8.9 |

Thus the FY2025 reserve-model Ce figure is 2.6 percentage points below its FY2024 counterpart, and La is 0.1 point below. The resource-model figures are unchanged. These are **changes in disclosed engineering assumptions**, not evidence of falling observed operating recovery, policy effects or industrial adaptation. Resource and reserve notes are not independent production samples.

The extractor binds every numeric value to its named product or denominator. It additionally binds resource/reserve quotes to the nearest original section heading. The FY2024 recovery passages have identical wording; a simple first regex match would silently collapse their distinct contexts. Match ordinals and heading checks preserve both.

Four descriptive constraints are also recorded from the FY2025 original:

1. Concentrator recovery varies with ore grade; the quoted note does not supply the function or a universal upstream recovery.
2. HREE are present but excluded from that resource estimate because of historic data limitations. Neither Dy/Tb abundance nor recoverable output is quantified; unknown is not zero.
3. The oxidizing roast facilitates early removal of cerium with insoluble gangue. Total concentrate REO is not automatically separated saleable oxide.
4. Midstream scope includes own concentrate and third-party/recycled feed. This statement supplies no finite third-party feed, origin certification, route capacity or verified inventory.

## Partial material constraint and executed checks

For native concentrate processed (q), an oxide-equivalent NdPr group obeys the necessary conditional bound

\[
 d_{\mathrm{NdPr,REOeq}}\leq q\,g_{\mathrm{TREO}}\,s_{\mathrm{NdPr}\mid\mathrm{TREO}}\,r_{\mathrm{NdPr}},
 \qquad 0\leq q\leq F.
\]

Here (F) must be a separately verified finite available feed before an industrial application. With the issuer's assumptions, the coefficient is

\[
0.60\times0.157\times0.897=0.0844974
\quad\text{tonne NdPr oxide-equivalent per native concentrate tonne.}
\]

The incoming NdPr-group oxide equivalent is 0.0942 tonne and the unrecovered amount is 0.0097026 tonne per native concentrate tonne. These calculations are conditional accounting, **not an estimated operating yield**. Reported input precision does not justify treating the displayed decimal expansion as measurement accuracy. Purity-qualified sale-product mass and separate Nd and Pr element masses are unidentified.

`src/weaponized/rare_earths/engineering.py` checks the different denominators, joint-share closure, nonnegative recovery and no creation of the accounted oxide-equivalent group. An independent two-variable linear program maximizes the grouped output subject to the finite feed and conditional coefficient. **Twelve checks** cover four source/context versions at normalized feeds 0, 0.5 and 1. All agree with their analytical bounds; zero feed permits zero output. These feed quantities are diagnostic normalizations, not observed stocks. Results remain in `outputs/diagnostics/engineering_inputs_validation.json`, physically separate from empirical supply results.

This is a necessary partial constraint, not a complete production activity or a finished-magnet recipe. The main physical LP requires individual contained elements; introducing a fictional “NdPr element,” pretending that La carbonate equals La oxide mass, or treating the normalized feed as observed inventory would violate that contract. The new output therefore does **not** create a ready-to-score activity in the main empirical service network. It can constrain an eventual versioned recipe once the missing element split, full material basis and other inputs/outflows are evidenced.

## Outputs and integration contract

Run after `scripts/build_rare_earths.py`:

```bash
.venv/bin/python scripts/build_engineering_inputs.py
.venv/bin/pytest -q tests/test_engineering_inputs.py
```

Actual execution: extraction passed; **11 tests passed**. Tests reject recovery above one, negative/nonfinite recovery or feed, double-counted joint shares, carbonate/oxide basis substitution, a nearby product's number and a quote taken from the wrong resource/reserve section.

| Output under `data/processed/engineering_inputs/` | Meaning and principal fields |
|---|---|
| `observations.csv` | 32 source claims. Native values/units/products; classification; resource/reserve context; exact quote/ordinal; reporting/public/retrieval clocks; URL/hash; interpretation; vintage-certification limitation. Planning inputs use Claim `evidence_class=calibrated`, while the four categorical disclosure observations use `empirical`. Neither designation means independent engineering validation. |
| `conditional_oxide_constraints.csv` | Four source/context necessary bounds with input/output basis, grade, grouped share, assumed recovery and source-claim IDs. Unknown stock, annual output, Nd/Pr split, sale-product mass and China-free service remain null. |
| `recovery_assumption_versions.csv` | Eight product/context comparisons between the two annual sources, preserving both values and hashes. Differences are in percentage points and explicitly labelled changes in assumptions. |

Unknown-function and unknown-quantity categories refer to the unmeasured process function and HREE flows, not missing source files. No laboratory result is included; none of these planning inputs is reclassified as a laboratory or independently measured commercial recovery.

Remaining empirical requirements are dated feed assays and composition distributions; separately measured Nd/Pr/Dy/Tb recoveries and chemical forms; throughput/ramp/capacity evidence; finite opening inventories and all external feed origins; coproduct and waste mass bases; other processing inputs; transport/contractual routes; qualified downstream production; and grade-specific final demand. The historical engineering assumptions supply useful conditional constraints but cannot close those independent measurements or identify annual China-free magnet service, N-1 robustness, transition hazards or forecast probabilities.
