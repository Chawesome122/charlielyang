# Reciprocal dynamic game: definitions, mathematical repair and numerical scope

The authority is blueprint §§8–9. Every numerical game primitive in
`configs/game.yaml` is **hypothetical**, including discount rates and growth rates.
There is no estimated national utility function, observed-policy baseline, or
empirically calibrated forecast. Game time is years; a quarter is 0.25 years.

## Dynamics and invariance

State order is \(s=(x,y,m,n)\). With
\(G_C(m)=g_C\exp(\beta_Cm)\), \(G_U(n)=g_U\exp(\beta_Un)\),

\[
\dot x=G_C(m)(1-x)-\delta_Cx,\quad
\dot y=G_U(n)(1-y)-\delta_Uy,\quad
\dot m=\kappa_C(u-m),\quad \dot n=\kappa_U(c-n).
\]

Require \(g_i,\kappa_i>0,\delta_i\ge0\), with unrestricted real \(\beta_i\).
At the lower and upper faces of each pipeline, the drift is respectively
nonnegative and nonpositive for all admissible controls. At \(x=0\), drift is
strictly positive; at \(x=1\), it equals \(-\delta_C\le0\), and similarly for
\(y\). The locally Lipschitz vector field therefore preserves the closed unit
hypercube. Negative induced adaptation changes a positive growth rate rather
than producing negative physical effort. Numerical integrators are checked for
violations; clipping a reported trajectory would conceal a failed integration.

For fixed controls, \(m^*=u,n^*=c\) and
\(x^*=G_C(u)/(G_C(u)+\delta_C)\),
\(y^*=G_U(c)/(G_U(c)+\delta_U)\). In pipeline-first ordering, the Jacobian is
block triangular, with eigenvalues
\(-\kappa_C,-\kappa_U,-(G_C(u)+\delta_C),-(G_U(c)+\delta_U)\).
They are strictly negative. The derivative \(\partial_m\dot x=\beta_CG_C(m)(1-x)\)
has unrestricted sign. This fixed-control stability result does not establish
feedback stability.

The exact quarterly pipeline update is
\(m_{q+1}=u_q+(m_q-u_q)e^{-\kappa_C/4}\). A constant-pipeline state update is exact
only conditional on holding the pipeline fixed; a changing pipeline requires
coupled integration. The code exposes both functions with different names.

## Payoffs and exact statewise action equilibria

Both flow payoffs are implemented directly from §8.3, including opponent
exposure, own convex control costs, mobilization costs on the opponent-induced
pipeline, own resilience benefits, and sign-free coupling. Positive discount
rates and bounded flow payoffs imply finite objective values; these conditions
alone do not imply pure feedback MPE existence.

For fixed smooth value gradients, let
\(M_U=A_U(1-x)+\kappa_C V_{U,m}\) and
\(M_C=A_C(1-y)+\kappa_U V_{C,n}\). The conditional best responses are
\(\Pi_{[0,1]}[(M_U+q_Uc)/k_U]\) and
\(\Pi_{[0,1]}[(M_C+q_Cu)/k_C]\). `solve_stage_nash` enumerates the nine combinations
of lower, upper and interior status and validates each against both conditional
best responses. Equality candidates are de-duplicated. Multiple matches are
retained rather than interpreted as uniqueness.

The blueprint's finite nine-regime table omits the singular interior case
\(\Delta=k_Uk_C-q_Uq_C=0\). When consistent, the interior linear equations can
have a continuum. For example \(k_U=k_C=q_U=q_C=1\), \(M_U=M_C=0\) gives all
\(u=c\in[0,1]\). The implementation records the whole feasible line segment as
`continuum_endpoints` alongside its midpoint; it also retains any isolated
boundary candidates. This is a substantive completeness repair to §8.4, not a
claim that the continuum implies multiple dynamic equilibria.

The published counterexample is verified: \(M_U=1.2,M_C=0.1,k_i=1,q_i=0.8\)
has action Nash \((1,0.9)\). Independent clipping of the interior simultaneous
solution produces \((1,1)\), against which China profitably deviates.

## Constant-control self-eroding leverage

In the separate one-sided benchmark \(\dot x=bu(1-x)\), fixed \(u\) gives
\(v(t)=v_0e^{-but}\). Integrating the discounted payoff yields

\[
J(u)=\frac{Auv_0}{\rho+bu}-\frac{ku^2}{2\rho},\quad
J'(u)=\frac{Av_0\rho}{(\rho+bu)^2}-\frac{ku}{\rho}.
\]

The nonnegative polynomial root satisfies
\(ku(\rho+bu)^2=Av_0\rho^2\), whose left side increases strictly for \(u\ge0\).
Project only this one-dimensional optimum onto the unit interval. At
\(A=v_0=k=\rho=b=1\), the root is approximately 0.465571231876768. Its residual,
numerical objective optimum, and independent improper payoff integral are
tested. It is a constant-policy result and does not solve unrestricted
time-varying control or the reciprocal game.

## Sparse state-constrained HJB approximation

On the tensor grid, the generator moves to the next node along a dimension
at rate \(f_j^+/h\), or the previous node at rate \(f_j^-/h\). Diagonal rates are
minus total outgoing rates. The generator has nonnegative off-diagonals and
zero row sums. At boundary faces, outward rates must be zero; the code raises
an error if the underlying drift violates this restriction. There are no
arbitrary zero-value Dirichlet boundaries. Each fixed-policy evaluation solves
\((\rho_iI-L^\sigma)V_i=\pi_i^\sigma\) by preconditioned BiCGSTAB, recording
iterations, actual residuals, sparse nonzeros, bytes, runtime and process peak
resident memory. Affine-function generator consistency and monotonicity are
unit tested.

A necessary correction to a literal implementation of §8.6 step 5 is that
upwind selection depends on the trial action. In the m dimension the drift
changes sign at \(u=m\). With backward and forward differences \(D^-V,D^+V\),
the action-dependent continuation term is

\[
\kappa_C(u-m)\begin{cases}D^-_m V_U,&u<m,\\D^+_m V_U,&u\ge m.\end{cases}
\]

Holding the derivative from the current action fixed during improvement need
not maximize the discrete Hamiltonian. It can give a small policy-evaluation
residual while leaving profitable deviations. Instead `improve_policies`
enumerates each player's statuses {0, lower-piece interior, pipeline kink,
upper-piece interior, 1}, making 25 joint combinations. For each algebraically
feasible pair it compares both players' full global piecewise maxima. The
global unilateral maximizer is found exactly among the two interval stationary
points, the kink and endpoints. This also handles a nonconcave kink. For
singular interior piece equations, incomplete finite enumeration is flagged;
the analytic nine-regime function separately represents singular continua.

All six prescribed starts are supported: zero, one, each asymmetric endpoint,
midpoint and seeded smooth random. Damped joint updates are followed by an
additional final evaluation, ensuring values correspond to reported policies.
Each result records both linear residuals and global unilateral gains. A tiny
linear residual by itself says only that the fixed-policy value solve worked.
The acceptance thresholds are HJB residual
\(10^{-8}(1+\|\pi_i\|_\infty)\), unilateral gain \(10^{-8}\), and action response
residual \(10^{-7}\). Numerical nonconvergence is retained as `not_solved`.

Accepted results are **verified finite-grid candidates** of a finite-state,
continuous-action discounted game. They are not certified continuous-state
pure MPE. The grid generator introduces artificial diffusion. Multistart
agreement tests possible numerical multiplicity only over explored starts;
refinement reports sup-norm policy changes and does not prove a continuum
limit. No empirical U.S. or Chinese optimal policy is inferred.

## Feedback stability and scenarios

`closed_loop_jacobian` differentiates the complete composed field
\(f(s,\sigma_U(s),\sigma_C(s))\), including policy-state derivatives. Stationary
roots must lie within the cube and satisfy the original drift. Multilinear
policy interpolation is piecewise differentiable: grid-knot distance is recorded
and resulting eigenvalues describe the interpolated scenario policy only.
At a knot, a central secant can mask an unstable one-sided derivative. Roots
within twice the differentiation step of any knot are therefore classified
`inconclusive_at_interpolation_knot`, with `locally_stable=None`, regardless of
the central secant's eigenvalue signs. One-sided/nonsmooth analysis is required
there. An independently suggested adversarial regression test verifies this rule.

The run script executes negative, zero and positive adaptation, strategic
patience, policy complementarity/substitution, and theoretical growth/licensing
parameter perturbations when requested. Trajectories include a candidate-policy
baseline, ±25% normalized control paths, and a one-year unilateral U.S. shock
with the opponent's initial action frozen for that year. The starting state
\((.25,.25,0,0)\) is hypothetical. Reported counterfactual payoffs integrate 30
years and explicitly omit terminal continuation. Their political-welfare
interpretation is conditional on assumed payoffs. Subsidy and licensing
parameter perturbations are scenario mappings rather than estimated mechanisms.
Opacity, plant outages and alternative technical architectures require their
independently validated empirical modules before quantitative integration.

If joint coupled policy iteration fails, `--method alternating` attempts
alternating full discounted-MDP best responses: each inner iteration optimizes
one player's complete dynamic problem while holding the opponent's feedback
policy fixed. This is a supported numerical alternative and does not guarantee
outer convergence in a general-sum game. Failed joint results remain archived
separately from alternate attempts. The final verification thresholds apply
unchanged to both methods.

## Empirical mapping and transition fitting: implemented, data-dependent

`game/calibration.py` constructs the literal minimum of registered essential
domestic layer capabilities and preserves missing essential evidence. It
rejects service fractions inferred from raw capacity ratios above one; the
rare-earth mapping requires delivered services from an independently validated
China-exclusion LP with frozen demand weights. Neither guard supplies missing
industrial evidence. No empirical game-state series has been inferred from
the hypothetical examples.

The module also supplies a measurement-error-weighted, multistart nonlinear
least-squares estimator for one side's full changing-pipeline dynamics. It
integrates piecewise constant quarterly controls with time measured in years.
Local Jacobian singular values, rank, conditioning and start objectives are
reported. The initial measured state and legal control observations are treated
as known, and the objective assumes supplied diagonal state uncertainties;
this is a descriptive reduced-form fit without an endogeneity correction.
Search bounds are numerical limits, not empirical intervals. The estimator
returns no confidence intervals without a justified observation model and
never reports a causal restriction effect. Synthetic tests recover known
parameters under varied exposures and diagnose the inability to identify beta
or pipeline adjustment from zero exposure. Synthetic recovery is engineering
validation, not validation of empirical predictive skill or four-state adequacy.

## Reproduction

Run `uv run pytest -q tests/test_game.py` and, for example,
`uv run python scripts/run_game.py --grids 17 21 --scenarios adaptation_positive`.
Archives, diagnostics, CSV trajectories and PDF/PNG figures are under
`outputs/scenario/game`. Each scenario/start/grid has a separate compressed
policy/value archive and diagnostic JSON. `summary_*.json` records mesh changes,
multistart distances, checksums and finite-horizon counterfactual payoffs.
