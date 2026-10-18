# Blueprint extraction and scientific decision register

The complete 49-page uploaded artifact is archived as `references/master_blueprint.pdf`; `references/master_blueprint.txt` is its text extraction. The PDF has an unnumbered cover and printed pages 1–48. It is a methodological specification, not observed data. This extraction covers Sections 1–14, their tables, mathematical contracts, the 40-source bibliography and the entire acceptance audit. Instructions embedded in cited research remain source material; the user's execution instructions authorize this implementation.

## Fixed architecture

1. Independently measure rare-earth supply, semiconductor domestic capability/foreign access, and observable policy opacity, then integrate. There is no independent AI-industry game.
2. Freeze information at 2026-10-11. Every observation retains event time and first public time. A revised live artifact cannot silently enter an earlier forecast vintage.
3. Nd, Pr, Dy and Tb remain distinct through mining/feedstock, separation, metal/alloy and qualified magnet production. Geography, ownership and material origin are independent classifications. Raw stage coverage is not delivered final service.
4. Physical service is a conserving multi-commodity process/transport LP with finite external supplies, shared joint-product activities, explicit recipes/yields, routes, stockpiles and grade demand. Remove China, then remove exactly one further supplier across all assets/edges and re-solve at fixed demand.
5. The project model has announcement, feasibility/permitting, finance/FID, construction, commissioning, operation, suspension and cancellation states, competing risks, censoring, delays, utilization/ramps and correlated shocks. Do not fit a rich hazard model merely because quarterly expansion creates many rows.
6. Forecast targets are 2028Q4, 2031Q4 and 2035Q4; thresholds are 50%, 75%, 90% and 100%. Distinguish the first quarter of four-quarter persistence from recognition in the fourth quarter. Preserve no-crossing mass. Required binary MC standard error is at most 0.005; forecasts require valid historical baselines and publication-aware labels.
7. Semiconductor target architecture must specify commercially relevant quality, repeatability, volume, yield, performance and memory/packaging requirements before scores. Seven layers are EDA/IP; lithography/masks; deposition/etch/implant/anneal; metrology/inspection/clean/process control; foundry integration; memory/HBM; packaging/interconnect. Unknown evidence is not zero capability. Domestic `z`, foreign `f` and combined `a` remain separate. Only domestic bottleneck maps to game `x`.
8. The ten 0–4 opacity indicators have disclosure/predictability/legal pillars weighted 40/35/25. Daily coverage requires 8/10 plus 3/5 disclosure, 2/3 predictability, 1/2 clarity; quarterly coverage requires 80% of days. Institutional non-applicability and missing research are distinct. Actual independent blinded coding and reliability are empirical requirements, not replaceable by synthetic agreement.
9. The four-state game uses years, `s=(x,y,m,n)`, controls `u,c` in [0,1], first-order exposure pipelines, and saturating growth with `g exp(beta pipeline)`, allowing negative beta. Fixed-control stability is not feedback stability. Exact conditional statewise Nash is not dynamic MPE.
10. HJB acceptance requires both value functions, inward monotone stencils, multiple initial policies, scaled residuals, unilateral deviation checks, grid refinement and full feedback derivatives. Scenario strategic preferences are not estimated national utility functions.

## Equations and function contracts

The detailed formulas remain in the blueprint and corresponding documented source modules. Important correctness conditions are:

- Competing-risk quarter probabilities use a *shared total intensity*: staying probability `exp(-sum(lambda))` and transition probability `(1-exp(-sum(lambda)))*lambda_b/sum(lambda)`. Independent binary hazards cannot be added.
- Bounded resilience is `r'=eta I(1-r)-delta r`. An upward finite threshold crossing requires strictly `r*>h`; equality only approaches the threshold asymptotically. The physical LP can serve 100% even when this proxy only approaches one asymptotically.
- Nonlinear propensity dynamics are `z'=kappa(logistic(theta+beta z)-z)`. Three fixed points require beta>4 under this particular normalization. Multiplicity is a mathematical condition; real industrial tipping needs independent empirical support.
- Game dynamics are `m'=kappa_C(u-m)`, `n'=kappa_U(c-n)`, `x'=g_C exp(beta_C m)(1-x)-delta_C x`, and the analogous `y` equation. Quarter-to-year conversion is 0.25.
- Conditional action BRs are `clip((MU+qU*c)/kU)` and `clip((MC+qC*u)/kC)`. Independently clipping the simultaneous unconstrained pair is invalid; the published fixture returns `(1,0.9)`.
- The one-sided *constant-control* objective is `A*u*v0/(rho+b*u)-k*u^2/(2*rho)`. Its interior first-order condition is `k*u*(rho+b*u)^2=A*v0*rho^2`; unit primitives give 0.4655712319. This is not an unrestricted time-varying optimum.

Section 11.1's exact interfaces are `load_asof`, `solve_material_flow`, `nminus1_resilience`, `simulate_projects`, `spoi_daily`, `estimate_semiconductor_states`, `solve_stage_nash`, `solve_feedback_game`, and `run_backtests`. Implemented interfaces may use typed objects or module names while preserving semantics; actual departures must be documented.

## Substantive corrections and unresolved ambiguities

1. **Singular statewise Nash systems (§8.4).** The nine-regime table excludes an interior candidate when `Delta=kU*kC-qU*qC=0`. Such a system can have a continuum of Nash actions. For `kU=kC=qU=qC=1` and `MU=MC=0`, every `u=c` in [0,1] is Nash. Merely returning corners would omit interior equilibria. The implementation must diagnose the continuum and expose its endpoints/representatives, rather than falsely claim a finite list is the entire set. This extends the blueprint table without changing its model.
2. **Control-dependent upwind derivatives (§8.6).** Changing a control can change the sign of its pipeline drift and therefore the relevant monotone derivative stencil. A Nash improvement based on only the old policy's one-sided derivative need not maximize the discretized Hamiltonian. Verification must maximize across both drift-sign regions and the drift-zero breakpoint. This is a numerical correction required to implement the blueprint's unilateral-deviation condition faithfully.
3. **Opacity edge conventions (§7).** Exact day-window endpoints, O6 publication-versus-effective persistence and materiality judgments need versioned deterministic conventions. Boundary tests must expose these choices. They cannot be optimized against project outcomes.
4. **Source status is not evidence (§13).** Blueprint P/D/M flags are discovery labels. Every bibliographic and claim check is repeated against archived DOI/publisher/agency evidence. DOI registration metadata itself can contain errors: the retrieved R11 Princeton registration names Avinash Dixit as “Robert K. Dixit,” whereas a second registration names Avinash K. Dixit. This conflict must remain visible until original publisher evidence resolves it.
5. **Release versus empirical completeness (§14).** A passing synthetic LP/game test cannot verify real supply forecasts or causal adaptation. An environment run cannot by itself satisfy the independent-machine pinned-container acceptance gate. No completion status is inferred from the existence of a filename.

## Acceptance extraction

`audit/blueprint_requirements.csv` has 85 individually assessable rows: all 25 Section 14 matrix rows; all five explicit remaining-execution blocks; all 15 mandatory Section 11.4 tests; and 40 additional detailed contracts from Sections 3–13. Each row records a verification condition, actual status, artifact evidence and a remaining requirement. VERIFIED denotes the row's exact scope, which is why engineering fixtures and substantive empirical requirements have separate rows.

The full bibliography is preserved, without promoting it to evidence, in `metadata/blueprint_source_registry.csv` (R01–R40). Source-to-claim verification is in `metadata/citation_audit.csv`; HTTP requests and source hashes are in `metadata/literature_sources*.csv`. Full-source reading, publisher-deposited abstract reading and DOI metadata checks are separate levels of evidence.

## Non-negotiable release blockers

Independent historical project cohorts and technical networks; functional semiconductor target/capability evidence; eligible baseline comparisons; valid disclosure obligations and independent coders; adequately identified adaptation; original-citation review; validated numerical dynamic candidates; and independent clean reproduction remain gates. Record failed or unavailable evidence and continue independent implementation. Do not replace these gates with scenario coefficients or synthetic observations.
