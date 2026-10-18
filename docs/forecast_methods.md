# Project transitions and forecasting: implementation and evidence boundary

This module implements blueprint §§3.2, 4 and 11. It does **not** supply empirical
rare-earth forecast probabilities. The current public-source collection does not
establish a frozen statistical project universe, an estimable event history, or a
verified industrial network. `outputs/diagnostics/forecast_readiness.json` records
the exact prerequisites. The twelve requested target/threshold combinations are
listed with **empty** probability cells in
`outputs/diagnostics/empirical_forecast_targets.csv`; empty is not zero.

## State and observation models

The states are A announced, F feasibility/permitting, I financing/FID, C
construction, Q testing/commissioning, O operating, S suspended and X cancelled.
The default progression is A→F→I→C→Q→O, with suspension and cancellation risks
from nonabsorbing states. X is absorbing. Suspension can resume only at its
recorded pre-suspension state in the project simulator (an announced suspension
resumes at feasibility); independently observed relaunches after cancellation
require a separately coded project/activity rather than an invented X exit.
Expansions require distinct activity IDs. Existing operating observations are
initialized with a commissioning date rather than counted as newly completed.

For one-quarter, cause-specific intensities λ_b and Λ=Σ_b λ_b produce

\[
 P_{aa}=\exp(-\Lambda),\qquad
 P_{ab}=\{1-\exp(-\Lambda)\}\lambda_b/\Lambda.
\]

The zero-intensity limit is P_aa=1. The shared exit probability normalizes all
causes jointly; independent binary complementary-log-log probabilities must not
be added. With one cause, log(-log(1-P_ab))=log λ_b. Intensities are per quarter.
Fractional first-quarter durations must be explicitly registered if simulation
begins during the origin quarter; ordinary forecasts begin the next quarter.

`TransitionModel` accepts registered duration slopes, lagged covariate coefficients,
calendar effects, and country/stage log intercepts. Required missing covariates
raise errors. The simulator currently holds the snapshot's lagged covariates
fixed, and uses scenario paths only for its common shocks. Empirical evolving
financing/offtake/subsidy/price covariates require independently sourced paths;
none have been estimated here.

Three observation likelihoods are deliberately distinguished:

1. Consecutive observed quarterly states contribute log P_ab.
2. Right-censored, **known physical survival** for k quarters contributes
   k log P_aa. A lack of press releases is not complete surveillance; the function
   refuses that interpretation without an explicit observation model.
3. Two observed endpoint states separated by k quarters contribute
   log[(P^k)_ab], integrating all allowed intermediate quarterly paths. This is
   an endpoint observation likelihood, not a first-passage likelihood when
   suspension/re-entry is possible. A separately implemented first-exit interval
   likelihood is log[Σ_{j=L}^U P_aa^(j-1)P_ab], requiring surveillance that identifies
   the first exit and its cause.

The likelihood helpers use a stationary, constant-intensity observation model.
They reject nonzero duration effects and conditional covariate/calendar models:
those require an age-augmented/product-of-time-varying-transition likelihood.
Matrix powers here describe **discrete quarterly paths**; substituting a CTMC
matrix exponential would silently allow several stage transitions per quarter.
Real retrospectively reported stage jumps therefore require interval observation
coding or a dedicated reporting-delay model, which remains an empirical task.

The executed constant-intensity estimator uses multinomial maximum likelihood.
Its minimum-event guards require at least ten observed exits per parameter and
five per cause; zero stay observations cannot identify a finite unpenalized total
intensity. These are engineering safeguards rather than a claim of statistical
sufficiency. Repeated panel rows do not create independent events. No empirical
hazard model, country random-effect variance or commissioning-delay coefficient
has been fitted. Rich duration/covariate effects support scenario evaluation, not
unearned parameter estimates or reported confidence intervals.

## Output and physical bridge

`RampSpec` implements step, exponential, logistic and observed-output ramps.
Documented annual tonne capacities are converted to quarterly envelopes by /4.
The exponential ramp is U C/4 [1-exp(-r(age+offset))], zero before commissioning;
offset zero gives zero capacity during the commissioning quarter. Step ramps
permit an immediate capacity change. Observed trajectories never extrapolate
without a separate registered model. These are capacity bounds, not output:
feedstock, yield and demand still constrain the physical LP.

`simulate_projects` requires independent named RNG streams and a callable
physical bridge. It cannot convert stage-capacity sums into service. Parameters
and physical quantities can be drawn through explicitly supplied callbacks.
Common stationary AR(1), supplier-group and idiosyncratic Gaussian log-intensity
shocks preserve dependence; lognormal mean corrections center unconditional
intensities. Group shocks also correlate activities at the same project/site.
Physical upstream exposure is enforced by shared feedstocks/routes in the LP.
Calibrating these shock variances requires data and remains unresolved.

The bridge is invoked for every path-quarter. A cache is valid only when its key
includes **all** quantities affecting the network. The executed demonstration
has stationary demand, routes, recipes, finite supplies and disposal channels,
and no inventory carryover; exact capacity patterns therefore form a sufficient
key. Networks with stock dynamics require a joint-horizon optimizer or inventory
state in the key, not this stationary cache.

## First-passage reporting and Monte Carlo accuracy

For threshold h, the start τ_h is the first quarter with four consecutive service
quarters at least h; recognition is τ_h+3. The numerical service tolerance is
10^-8, consistent with the LP's declared numerical tolerance. Start-by-T needs
simulation through T+3; the summary function refuses an insufficient horizon.
The targets are 2028Q4, 2031Q4 and 2035Q4, each at h=0.5, 0.75, 0.9 and 1.0.
No-crossing-through-horizon mass is retained in quantiles as an explicit flag,
not dropped to produce falsely finite medians. Predictive quantiles are not
confidence intervals on model parameters.

For independent equal-weight draws, MCSE=sqrt[p(1-p)/N]. Ten thousand draws
guarantee the blueprint's 0.005 worst-case MCSE. Effective sample size can be
supplied for correlated/weighted estimates, but the current simulation produces
independent equal-weight paths. The reported Wilson intervals describe Monte
Carlo sampling error only. Zero simulated events do not establish zero event
probability; their Wilson upper bound remains positive.

## Historical eligibility, baselines and scores

`forecast.origins` registers all fifteen origin/horizon combinations from the
blueprint's 2016/2018/2020/2022/2024 year-end origins and 2/4/6-year horizons.
October 11, 2026 is inclusive. Future endpoints are rejected mechanically; past
endpoints still require an actual outcome release by the freeze and an available
frozen forecast vintage. A December 2023 event first published in 2024 never
enters the December 2023 information set. Missing publication dates are excluded.
The output eligibility table currently has no verified outcomes to score.

The code implements zero-new-build, announced-on-time, historical-mean-delay,
linear and aggregate-logistic baselines. The first two schedule baselines still
call the physical network; aggregate trends are explicitly descriptive. The
mean-delay baseline requires at least five origin-eligible historical completions
and discloses survivor selection. Baseline availability failures must remain in
the comparison audit; no failed or unfavourable origin can be silently removed.

Scores include Brier, negative log score, exact ensemble CRPS and predictive
interval coverage. Incorrect certainty has infinite log loss, explicitly encoded
in JSON. IPCW time-dependent Brier scores correctly retain competing realized
events as observed noncommissioning outcomes, require positive censor-survival
weights, and depend on conditional independent censoring. Aalen–Johansen marginal
cumulative incidence is implemented for ordinary right-censored risk sets.
Left truncation and covariate-adjusted censoring require extended risk sets.
Reliability bins are descriptive. Bootstrap utilities resample project-parent
clusters and crossed project/calendar-origin multiplicities, rather than treating
overlapping panel rows as independent. Small cluster counts remain an inference
limitation.

## Executed synthetic engineering checks

Run from the repository root:

```sh
uv sync --frozen
uv run pytest -q tests/test_forecast.py tests/test_forecast_physical.py
uv run python scripts/run_forecast.py --draws 10000
```

Fifteen tests passed in the recorded development run. The integrated demonstration
simulated 10,000 independent paths over 2026Q4–2036Q3 from a **synthetic**
September 30, 2026 snapshot. It used three finite four-stage Nd/Pr/Dy/Tb supplier
chains; all upstream sites were conditionally already operating, while final
magnet-project commissioning, suspension and cancellation were uncertain. Every
supplier outage removed its complete chain. Eight exact capacity patterns
required 24 physical LP/outage evaluations. All service probabilities met MCSE
≤0.005; maximum reported physical balance residual was zero. These are software
validation results, not estimates of real-world rare-earth development.

An independent synthetic train/test recovery exercise used 30,000 training and
10,000 held-out quarterly observations. True Q→O/Q→X intensities 0.25/0.08 were
recovered as 0.252025/0.081212. Held-out Brier was 0.170032, versus 0.25 for the
uninformative 0.5 predictor; negative log score was 0.523366. Finite-sample scores
can favour an estimate over the generating probability by chance. This exercise
does not establish historical forecasting skill, superiority over the complete
industrial baseline set or identification of empirical transition parameters.

Outputs are physically separated under `outputs/synthetic/forecast/`: compressed
draws, threshold summaries, parameter recovery, baseline paths, diagnostics and
a figure whose title explicitly states “SYNTHETIC”. `--skip-synthetic` regenerates
only the empirical readiness/endpoint audit.

## Remaining requirements

The empirical forecasting gate requires a registered inclusive project universe;
dated archived transition histories with an explicit observation protocol;
capacity/ownership/feedstock/yield/route/recipe/demand evidence; independent
commissioning and qualified-output observations; completed-project delay and
ramp histories; source releases sufficient for eligible historical endpoints;
and enough independent transitions for the registered model complexity. The
current implementation does not estimate a hierarchical hazard model, posterior
parameter uncertainty, reporting-delay distribution or endogenous project-entry
model. Historical backtests, empirical calibration, bottleneck uncertainty and
real 2028/2031/2035 probabilities remain **BLOCKED**, not validated by synthetic
Monte Carlo execution.
