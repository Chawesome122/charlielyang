# Physical optimization and Section 5 mathematical verification

The LP implementation is `src/weaponized/rare_earths/lp.py`; mathematical fixtures
are `rare_earths/resilience.py`. These fixtures are synthetic and provide **no
estimate of actual China-free supply or of a forecast probability**. Element
identities, finite feedstocks, joint processes and native product forms remain
explicit. `outputs/diagnostics/physical_readiness.json` records the empirical gap.

## Registered network

A commodity has a native tonne basis and an element-mass vector. Consequently a
tonne of Nd2O3 contains only 0.85735 tonnes Nd (the exact value follows the source
code's stated atomic masses), whereas the blueprint A/B fixture intentionally
uses contained-NdPr-equivalent tonnes throughout. Mixed NdPr oxide cannot be
converted without its composition. Annual capacity is divided by four only under
an explicitly selected uniform-calendar convention.

For node v, commodity k and consecutive quarter t, the equality implemented is

`Z[v,k,t] - Z[v,k,t-1] - M[v,k,t] - incoming F - output d*q + outgoing F + input b*q + final recipe*service = 0`.

The first-quarter right-hand side is the verified opening inventory. There are no
implicit external feeds. All feed, process, route, storage, and shared-resource
capacities are finite and nonnegative; missing capacities raise errors. An absent
edge is unavailable. Missing empirical edges must therefore be resolved or
registered as sensitivity alternatives before an empirical network is claimed.

Each joint process has exactly one activity variable. Its output contained mass
cannot exceed its input contained mass for any element. Finite disposal activities
are explicitly marked `kind="disposal"`; their material is counted as loss. They
are needed for the four-element fixture because separated coproduct proportions
differ from a finished magnet recipe. Excess Nd oxide cannot magically become Tb.
Other magnet constituents Fe/B enter through an explicit finite external feed.

Primary optimization maximizes the equal-quarter average of the frozen weighted
grade-service fractions. For a multi-quarter problem this objective is an explicit
registered averaging choice; it may allocate scarce stock to any quarter when
quarter priorities tie. A secondary LP minimizes shipping and imported-input use
while retaining primary service within `1e-10`. Fixed input ordering and HiGHS
produce repeatable allocations, though economically equivalent LP optima may
remain. The output reports each quarter's delivered quantities and minimum
essential-grade fraction, so the horizon average cannot conceal a shortage.

Removing a supplier removes every matching facility, activity, external feed,
owned inventory, route right, and explicitly tagged origin commodity. Demand is
held fixed. Excluding a logistics supplier only removes matching routes. An origin
tag on an intermediate commodity must be inherited by outputs sharing that
element; this rejects silent relabeling of Chinese-origin stocks. Feed exclusions
also propagate by physical conservation even when intermediates have generic
commodity names. Origin/ownership uncertainty requires separately registered
networks. `nminus1_resilience` rebuilds the LP once per **single** additional
supplier and reports the smallest resulting service.

Acceptance includes unit-scaled node balance residuals (`atol=1e-8` tonnes plus
`rtol=1e-8` times row throughput), capacity feasibility, primary-objective loss,
dual stationarity, primal-dual gap and complementary slackness. Marginal service
bottlenecks use the primary LP's duals, not the shipping-minimization duals. The
solver never repairs infeasibility with unrestricted imports.

The convenience Monte Carlo bridge is explicitly stateless and rejects opening
inventory or storage. Inventory-coupled forecasts must solve a joint horizon. Its
default raw metric sums nominal final-magnet output capacity for exactly one
grade/product and divides by same-basis demand, leaving all upstream feasibility
to the service LP. Heterogeneous grades require a separately registered raw metric.

## Executed fixtures

The blueprint A/B fixture has explicit separated feed/conversion and feasible
inter-group routing. Both suppliers serve 1; remove A gives 1/2; remove B gives
4/7. N-1 service is 1/2. Raw final-capacity coverage 75/70 exceeds one and remains
distinct from delivered service.

The four-element fixture uses four physical stages, chemically specified native
oxides, finite ore and Fe/B supplies, fixed magnet composition, and capacity-bound
joint separation. Installed service is 40/60; removing upstream owner A leaves B's
downstream plants physically starved. Removing the explicit Fe/B supplier also
eliminates service. These are numerical verification results, not observations of
named industrial firms. A separate two-quarter test proves ten opening tonnes
cannot serve ten tonnes in each quarter.

## Bounded resilience ODE

For A=eta*I and lambda=A+delta, `dr/dt=A-(A+delta)r`. At 0 the vector field is
nonnegative and at 1 it is nonpositive, proving forward invariance. When lambda>0,
the unique equilibrium is A/lambda and the solution is

`r(t)=A/lambda + (r0-A/lambda)*exp(-lambda*t)`.

The eigenvalue is -lambda. For r0<h<r*, upward crossing time is
`log((r*-r0)/(r*-h))/lambda`. Equality r*=h gives asymptotic approach, not finite
crossing. Exact h=1 is unreachable from below at finite time. This fact does not
preclude a physical network from serving 100% of a bounded demand quantity.

**Documented boundary-case repair to Section 5.1:** its allowed primitives include
I=delta=0, hence lambda=0. The printed strict inequality -lambda<0 and division
A/lambda do not apply there. Every state is then a neutral equilibrium and
`r(t)=r0`; the implementation handles this explicitly. The unique stable-state
claims require lambda>0. This repair preserves the intended model.

## Logistic feedback and genuine folds

For `dz/dt=kappa*(expit(theta+beta*z)-z)`, inward boundary signs again prove
invariance. Fixed points satisfy `theta=logit(z)-beta*z`; the local eigenvalue is
`kappa*(beta*z*(1-z)-1)`. Ordinary folds require beta>4, with

`z+-=(1+-sqrt(1-4/beta))/2`, `theta+-=logit(z+-)-beta*z+-`.

Three roots exist strictly between the two ordered theta fold values. The two
outer roots are stable and the central root unstable. At ordinary folds the second
state derivative is `kappa*beta*(1-2*z)`, which is nonzero. The roots are computed
in log-odds coordinates to avoid unstable endpoint logarithms.

At beta=4, theta=-2, the sole fixed point z=1/2 has zero linear eigenvalue but
`dz/dt=-(4/3)*kappa*(z-1/2)^3 + O((z-1/2)^5)`. It is asymptotically stable with
algebraic convergence, and is the codimension-two cusp degeneracy rather than a
pair of ordinary folds. The code and tests distinguish this case.

No beta has been estimated from historical industrial data. The bifurcation
figures show conditional model geometry. Physical cascading shortages, aggregate
capacity growth and an adequacy crossing do not establish endogenous feedback,
causal tipping, or hysteresis.

## Reproduction

Run `uv run pytest -q tests/test_materials.py tests/test_lp.py tests/test_dynamics.py`
and `uv run python scripts/run_physical.py`. This regenerates all JSON, CSV, PDF,
and PNG files in `outputs/synthetic/physical/`, including a local checksum
manifest. Figures and captions explicitly label their synthetic/scenario status.
