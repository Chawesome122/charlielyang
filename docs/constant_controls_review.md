# Reciprocal constant-commitment benchmark

Blueprint §8 permits accurately labeled constant-policy benchmarks when full feedback verification is unavailable. This extension retains the original four states, bounded dynamics and both complete payoff functions. At time zero each player commits to a single constant action forever, at the registered hypothetical initial state `(x,y,m,n)=(.25,.25,0,0)`. A unilateral deviation is another constant. This is neither feedback MPE nor unrestricted time-varying open-loop Nash. It is not an estimate of actual national preferences or policies.

## Derivation and sufficient conditions

Each own-action state subsystem is independent of the opponent's constant action. Dropping terms independent of own action, write `F_i(v;w)=a_i*v*W_i(v)-k_i*v²/(2*rho_i)+q_i*v*w/rho_i`, with `W_i=integral exp(-rho_i*t)*(1-z_i(t;v)) dt`. US `z=x`, China `z=y`. The full payoff is still integrated separately; only the best-response optimization drops constants.

For pipeline `M=v+(M0-v)*exp(-kappa*t)`, let `ell=1-exp(-kappa*t)`, `G=g*exp(beta*M)`. Then `z'=G*(1-z)-delta*z`. The first and second own-action sensitivities satisfy

- `xi'=G*beta*ell*(1-z)-(G+delta)*xi`;
- `zeta'=G*beta²*ell²*(1-z)-2*G*beta*ell*xi-(G+delta)*zeta`.

Initial sensitivities are zero because the initial state is fixed. Put `Gmin=g*exp(min(beta,0))`, `Gmax=g*exp(max(beta,0))`, `lambda0=Gmin+delta`. Scalar comparison and integration of the discounted convolution imply

`S = Gmax*abs(beta)/(rho*(rho+lambda0)) >= integral exp(-rho*t)*abs(xi) dt`,

`R = Gmax*beta²/(rho*(rho+lambda0)) + 2*Gmax*abs(beta)*S/(rho+lambda0) >= integral exp(-rho*t)*abs(zeta) dt`.

For nonnegative beta, `xi>=0` and `W'<=0`. Therefore `F'' <= a*(R+2*S*1[beta<0])-k/rho = -mu`. If both margins `mu>0`, box-constrained best responses are unique, and their Lipschitz bounds are `L_i=abs(q_i)/(rho_i*mu_i)`. If `L_U*L_C<1`, their scalar composition maps the compact interval into itself and is a contraction: the restricted commitment Nash exists and is unique for the fixed initial state. Boundary solutions use the box KKT inequalities. These are sufficient conditions; failure of these bounds would not prove nonexistence. This is an application of standard sensitivity, strict concavity and contraction arguments, not a claim of a new general dynamic-game existence theorem. The manuscript appendix gives the proof.

At beta zero, `z*=g/(g+delta)` and `W=(1-z*)/rho+(z*-z0)/(rho+g+delta)`. The benchmark reduces exactly to the existing simultaneous constrained stage game with `M_i=rho_i*a_i*W_i`, original costs and cross-action coefficients. Tests include the `(1,.9)` clipping counterexample.

## Executed results

`configs/constant_controls.yaml` registers nine original model scenarios, three initializations, tolerances, horizons and 129-point unilateral profiles. Run:

```bash
uv run python scripts/run_constant_controls.py
uv run pytest -q tests/test_constant_controls.py
```

All nine scenarios satisfy the sufficient restricted uniqueness bounds. Across 27 starts, maximum action spread is `5.225e-12`. There are 2,322 unilateral profile points, one exact beta-zero solution check, 54 independent full-original-payoff decomposition comparisons and 18 tighter-quadrature checks. Maximum refined KKT gradient error is `5.743e-12`; maximum full-payoff decomposition difference is `3.505e-12`. The largest analytic omitted infinite-payoff tail bound is `2.755e-13`.

With otherwise canonical hypothetical parameters, the negative/zero/positive beta scenarios give `(u,c)` approximately `(.62864,.63822)`, `(.54358,.55721)`, `(.46906,.48359)`. This ordering is a conditional scenario result, not an empirical adaptation estimate or general reciprocal-game theorem. Patience, complementarity, growth support and a licensing-value input are also varied in the original registered parameter scenarios.

The finite integration endpoint is `32/min(rho_U,rho_C)` years (80–320 years), chosen to bound mathematical tails. It is not a historical or real-world industrial forecast. Absolute full-payoff tails are bounded using `a+d+k/2+h/2+b+abs(q)` times `exp(-rho*T)/rho`. Sensitivity tails use uniform comparison bounds. DOP853 integration is checked at tighter tolerances and against exact beta-zero results; it is not interval arithmetic and does not provide a floating-point interval certificate. No utility confidence interval, policy calibration, feedback equilibrium or unrestricted open-loop equilibrium is inferred.

Outputs: `outputs/scenario/constant_controls/analysis.json`, five reproducible CSVs, nine detailed scenario JSONs, two figures, and `manuscript/constant_controls_table.tex`. Original numerical-core files remain unchanged; the new module is `src/weaponized/game/constant_controls.py`.

Combined release evidence: `outputs/diagnostics/final_release_validation.json` verifies the host and network-disabled container, including all 340 tests, all 88 registered artifact comparisons and exact manuscript text reproduction. The nine benchmarks were recomputed in both environments. This is same-host clean-container reproduction, not a second independent machine or empirical calibration.
