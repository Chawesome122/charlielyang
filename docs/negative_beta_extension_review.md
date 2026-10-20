# Additional negative-adaptation solver attempts

The previously recorded negative-beta fine-grid runs did not satisfy nonlinear unilateral/action criteria despite small linear policy-evaluation residuals. `configs/negative_beta_extension.yaml` registers three additional initializations of the unchanged original model and solver: zero, one and seeded random, each at `17^4=83,521` nodes and 160 policy iterations. Both adaptation betas remain `-.7`; seed is 101. The original economic parameters, algorithm and thresholds are unchanged, and the solver file hash is pinned.

```bash
OPENBLAS_NUM_THREADS=1 uv run python scripts/run_game.py --grids 17 --scenarios adaptation_negative --starts zero one random --max-iterations 160 --out outputs/scenario/negative_beta_extension --no-figures
uv run python scripts/audit_game.py --out outputs/scenario/negative_beta_extension
uv run python scripts/analyze_negative_extension.py
```

All three attempts finished `not_solved`. Their maximal global unilateral gaps are `3.20224e-5`, `1.00375e-3`, and `2.48225e-2`; their best-response action residuals are `.0118487`, `.0768039`, and `.311307`, respectively. Acceptance requires gain `<=1e-8` and action residual `<=1e-7`, alongside the scaled HJB criterion. Small linear residuals around `1.1e-10`–`1.9e-10` do not cure the failure of the Nash conditions. Each run exhausted its 160-iteration budget; iteration histories and largest-residual state locations remain archived. Runtime was approximately 223, 256 and 227 seconds.

The independent saved-array audit checks the actual policies, values, grid, hashes, Bellman residuals and unilateral deviations. Passing archive/status validation means the failure was correctly preserved; it is not a passing equilibrium test. There are zero accepted candidates in this extension. The earlier 34 accepted / three not-solved baseline records remain separate. There are therefore three *additional* failures, not three additional accepted candidates. No conclusion of equilibrium nonexistence or empirical policy behavior follows. The fraction of equally weighted grid nodes failing a condition is a numerical spatial diagnostic, never an empirical state probability.

Default replication re-audits the saved arrays and regenerates the diagnostic table and figure. `scripts/replicate.py --full` executes the registered solves again as well. The disconnected extension check re-audits these arrays; it does not re-solve them. A future solver modification should be a separately registered experiment with independent verification, not an alteration of these archived outcomes or weaker tolerances.

Evidence: `outputs/scenario/negative_beta_extension/analysis.json`, `registered_attempts.csv`, `iteration_history.csv`, `largest_action_residual_nodes.csv`, three saved NPZ arrays and iteration JSONs, the independent audit, `solver_diagnostics.pdf/png` and `manuscript/negative_extension_table.tex`.

Combined release evidence: `outputs/diagnostics/final_release_validation.json`. The three additional solves were executed on the host; the disconnected container independently re-evaluated their saved arrays and reproduced the diagnostic CSVs. It did not re-solve the additional HJB systems. The original 34 accepted finite-grid candidates remain distinct from these three additional failed attempts and from the nine restricted constant-commitment benchmarks.
