# Fixed-opponent dynamic deviations on the finite-state model

This extension implements the blueprint §8.6 unilateral dynamic verification gate without changing the original four-state model, sparse generator, action domain or full-game Nash thresholds. It holds one archived opponent **state-dependent feedback policy** fixed and solves the other player's discounted CTMC control problem on the original grid. It does not jointly update both players or produce a new full-game equilibrium. The CTMC approximation is distinct from the deterministic continuous-state ODE.

## Exact-arithmetic error bounds

Fix player i and the opponent feedback. For each admissible own feedback action, the original generator has nonnegative off-diagonal elements and row sum zero. All rates and rewards are bounded on a finite grid with compact actions. Uniformization by a common dominating jump rate gives a discounted Bellman contraction, so the optimal finite-state value V* exists and admits a stationary deterministic policy. This statement concerns the unilateral discounted MDP, not general-sum Nash existence.

For the original own policy pi and an approximate policy value V, define

- R_pi = rho V - r_pi - L_pi V;
- E = ||R_pi||_infinity;
- G(s) = max_a {r_a(s) + [L_a V](s)} - {r_pi(s) + [L_pi V](s)} >= 0;
- G_max = max_s G(s).

The exact policy value V_pi obeys ||V - V_pi||_infinity <= E/rho, because `(rho I-L_pi)^(-1)` is positive and has sup norm 1/rho. The optimal Bellman residual is `G-R_pi`. Shifting V upward by `(G_max+E)/rho` makes a supersolution, since every generator annihilates a constant. Bellman comparison therefore gives

`0 <= V* - V_pi <= (G_max+2E)/rho`.

Next evaluate an explicit unilateral feedback policy mu, yielding approximate W with policy residual sup norm E_mu and global Hamiltonian gap G_mu,max. For every model grid state,

`lower(s) = max(0, W(s)-V(s)-(E+E_mu)/rho) <= V*(s)-V_pi(s)`,

`V*(s)-V_pi(s) <= min((G_max+2E)/rho, max(0, W(s)-V(s)+(E+E_mu+G_mu,max)/rho)) = upper(s)`.

The lower bound follows from V* >= V_mu and the two policy-evaluation error bounds. The refined upper bound applies the same Bellman supersolution comparison to W. The reported global quantities are the maxima of these lower/upper functions over **all model grid states**, separately by player. They do not use empirical state weights or identify probabilities, national welfare or policy effects.

The inequalities are exact-arithmetic theorems. This implementation evaluates residuals and sparse solutions using ordinary floating-point arithmetic; it does **not** use directed rounding or interval-certified linear algebra. Consequently reported numerical endpoints are residual-adjusted diagnostics, not rigorous floating-point interval certificates or empirical confidence intervals. The discount is the original annual discount rate and generator rates are per year; dividing utility/year residuals by rho gives discounted utility units.

## Algorithm and checks

`src/weaponized/game/dynamic_deviation_audit.py` runs one-player Howard policy iteration with the opponent array copied and held exactly fixed. Each improvement globally maximizes over both directional pipeline-drift pieces and their common kink using the original exact piecewise maximizer. Each linear evaluation solves only the audited player's discounted equation with SciPy BiCGSTAB/Jacobi and a recorded GMRES fallback; a direct sparse solve supplies independent small-grid checks.

The registered own-MDP conditions are global Hamiltonian gap <=1e-11 **and** policy-evaluation residual <=1e-8*(1+reward sup norm), with linear relative tolerance 1e-12 and at most 100 iterations. These additional own-MDP diagnostic tolerances do not alter any original full-game acceptance threshold. Exhausted attempts retain their actual policy/value pair and report `solved_own_mdp=False`; a small gain cannot hide a failed linear evaluation. Even an unconverged explicit deviation can provide a lower bound and the baseline comparison upper bound.

The archive loader reads one byte snapshot, checks the pinned SHA256, and loads that same snapshot. It checks model primitives, dimensions, axes, policy box bounds and finite values. Original diagnostics and NPZ arrays are never overwritten. Each new saved audit records original-array and diagnostic hashes and its own output-array hash. Residual/gap uncertainty is distinct from mesh error, empirical state uncertainty and strategic parameter identification.

An internal independent computational review confirmed the comparison formulas and player axes; its suggested explicit scaled evaluation-status condition was implemented. This is not external specialist review or independent-machine replication.

## Executed results

Four original array archives are registered in `configs/dynamic_deviation_audit.yaml`, each with both players audited:

| Original archive | Player | Own-MDP iterations | Residual-adjusted global lower gain | Refined global upper regret |
|---|---|---:|---:|---:|
| positive response, 17 nodes, zero start | U.S. | 1 | 0 | 2.3718e-10 |
| positive response, 17 nodes, zero start | China | 1 | 0 | 5.3428e-10 |
| positive response, 21 nodes, zero start | U.S. | 1 | 0 | 4.4753e-10 |
| positive response, 21 nodes, zero start | China | 1 | 0 | 1.7953e-10 |
| failed negative response, 17 nodes, mid start | U.S. | 3 | 1.3213041e-4 | 1.3213157e-4 |
| failed negative response, 17 nodes, mid start | China | 3 | 1.5781606e-4 | 1.5781797e-4 |
| failed negative response, 17 nodes, additional zero start | U.S. | 3 | 1.1280833e-5 | 1.1281990e-5 |
| failed negative response, 17 nodes, additional zero start | China | 3 | 1.2849690e-5 | 1.2850024e-5 |

All eight own-MDP solves meet their registered gap/evaluation conditions. The positive-response cases are consistent with the original accepted finite-grid labels. The four explicit positive deviation gains for failed negative-response policy pairs demonstrate profitable dynamic deviations against those particular frozen opponents in the finite-state approximation. They do not imply that no other equilibrium exists, that the deterministic continuum is solved or that any actual policy is suboptimal. The maxima generally occur at different grid states; summing player maxima would not be a common-initial-state welfare comparison.

Eleven focused tests pass, covering an independently enumerated two-state CTMC MDP, exact inverse-discount error scaling, a zero-beta/zero-benefit special case with exact own optimum, both players' iterative versus direct sparse evaluations, exhausted-budget consistency, failed-evaluation status despite zero gain, invalid inputs and corrupt/mismatched source archives. Small numerical fixtures are explicitly synthetic tests.

## Reproduction and outputs

```bash
OPENBLAS_NUM_THREADS=1 uv run python scripts/run_dynamic_deviation_audit.py
uv run pytest -q tests/test_dynamic_deviation_audit.py
```

Outputs under `outputs/scenario/dynamic_deviation_audit/`:

- `analysis.json`: source/solve/frozen-opponent/bound counts and scientific-label guards;
- `value_bounds.csv`: eight per-player finite-state global regret records;
- `source_archives.csv`: four original paths and source SHA256 values;
- `policy_iteration_history.csv` and `diagnostic_states.csv`: actual iteration residuals and states attaining the numerical extrema;
- eight per-player JSON/NPZ pairs: saved own/opponent policies, original/optimized values, statewise bounds and output hashes;
- `value_bounds.pdf/png` and `table.tex`: reproducible exhibit and table. Zero lower endpoints are displayed at 1e-16 solely for the logarithmic axis; the CSV/table retain exact zero lower values.

Executed logs: `outputs/diagnostics/dynamic_deviation_audit_tests.log` and `dynamic_deviation_audit_run.log`. A later integrated release must verify the exact code version and reproduce these artifacts; this memo alone is not release certification.
