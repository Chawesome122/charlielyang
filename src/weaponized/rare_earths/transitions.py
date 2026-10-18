"""Coherent categorical competing risks and explicit observation likelihoods.

The quarterly model allows at most one transition per quarter. It is not a CTMC
matrix exponential, which could silently permit several physical stage jumps.
"""
from dataclasses import dataclass, field
from typing import Mapping
import numpy as np
from scipy.optimize import minimize
from .projects import ALLOWED, STATES


def competing_probabilities(intensities: Mapping[str, float], duration: float = 1.0) -> dict[str, float]:
    """Return stay/exit probabilities from cause-specific intensities per quarter."""
    if duration <= 0 or not np.isfinite(duration):
        raise ValueError("Duration must be finite and positive")
    rates = np.asarray(list(intensities.values()), dtype=float)
    if np.any(~np.isfinite(rates)) or np.any(rates < 0):
        raise ValueError("Intensities must be nonnegative and finite")
    total = float(rates.sum())
    if not np.isfinite(total):
        raise ValueError("Total intensity overflow")
    if total == 0:
        return {"stay": 1.0, **{s: 0.0 for s in intensities}}
    exit_mass = -np.expm1(-duration * total)
    return {"stay": float(np.exp(-duration * total)),
        **{s: float(exit_mass * rate / total) for s, rate in intensities.items()}}


@dataclass(frozen=True)
class TransitionModel:
    rates: Mapping[tuple[str, str], float]
    # Registered duration slope, by source state, on log(age + 1).
    age_slopes: Mapping[str, float] = field(default_factory=dict)
    provenance: str = "scenario"
    covariate_coefficients: Mapping[tuple[str, str], Mapping[str, float]] = field(default_factory=dict)
    calendar_log_offsets: Mapping[tuple[str, str, int], float] = field(default_factory=dict)
    country_log_offsets: Mapping[tuple[str, str, str], float] = field(default_factory=dict)
    stage_log_offsets: Mapping[tuple[str, str, str], float] = field(default_factory=dict)

    def __post_init__(self):
        for (a, b), value in self.rates.items():
            if b not in ALLOWED.get(a, ()) or value < 0 or not np.isfinite(value):
                raise ValueError(f"Invalid transition intensity {a}->{b}")

    def probabilities(self, state: str, age: int = 0, log_shock: float = 0,
                      resume_state: str | None = None, duration: float = 1.0,
                      *, covariates=None, calendar_quarter=None, country=None, stage=None) -> dict[str, float]:
        if state not in STATES or age < 0 or not np.isfinite(log_shock):
            raise ValueError("Invalid state, age or shock")
        eligible = ALLOWED[state]
        if state == "S":
            if resume_state not in STATES[:6]:
                raise ValueError("Suspension restart destination must be recorded")
            eligible = (resume_state, "X")
        rates = {}
        for b in eligible:
            coefficients = self.covariate_coefficients.get((state, b), {})
            if any(feature not in (covariates or {}) for feature in coefficients):
                raise ValueError("Required lagged covariate missing; absence is not zero")
            if self.calendar_log_offsets and calendar_quarter is None:
                raise ValueError("Calendar quarter required for registered calendar effects")
            if self.country_log_offsets and country is None:
                raise ValueError("Country required for registered country effects")
            if self.stage_log_offsets and stage is None:
                raise ValueError("Stage required for registered stage effects")
            age_slope = self.age_slopes.get((state, b), self.age_slopes.get(state, 0))
            log_multiplier = age_slope * np.log1p(age) + log_shock
            log_multiplier += sum(beta * covariates[feature] for feature, beta in coefficients.items())
            log_multiplier += self.calendar_log_offsets.get((state, b, calendar_quarter), 0)
            log_multiplier += self.country_log_offsets.get((state, b, country), 0)
            log_multiplier += self.stage_log_offsets.get((state, b, stage), 0)
            if not np.isfinite(log_multiplier) or abs(log_multiplier) > 700:
                raise ValueError("Intensity multiplier nonfinite or over/underflow")
            rates[b] = self.rates.get((state, b), 0) * np.exp(log_multiplier)
        probs = competing_probabilities(rates, duration)
        return {state if b == "stay" else b: p for b, p in probs.items()}

    def matrix(self) -> np.ndarray:
        """Stationary, age-zero observation model; S requires explicit rates in rates."""
        if any(value != 0 for value in self.age_slopes.values()):
            raise ValueError("Duration-dependent likelihood requires an age-augmented state; stationary matrix is invalid")
        if self.covariate_coefficients or self.calendar_log_offsets or self.country_log_offsets or self.stage_log_offsets:
            raise ValueError("Conditional likelihood requires registered covariate/calendar paths; baseline matrix is invalid")
        matrix = np.zeros((len(STATES), len(STATES)))
        for i, state in enumerate(STATES):
            probs = competing_probabilities({b: self.rates.get((state, b), 0) for b in ALLOWED[state]})
            for destination, p in probs.items():
                matrix[i, i if destination == "stay" else STATES.index(destination)] = p
        return matrix


def exact_loglik(model: TransitionModel, observations: list[tuple[str, str]]) -> float:
    """Consecutive quarterly observed states under complete state surveillance."""
    matrix = model.matrix()
    probabilities = [matrix[STATES.index(a), STATES.index(b)] for a, b in observations]
    return float(np.log(probabilities).sum()) if all(p > 0 for p in probabilities) else -np.inf


def right_censored_loglik(model: TransitionModel, state: str, quarters: int,
                         *, complete_surveillance: bool) -> float:
    """Known no physical exit through censor date, not merely no news of an exit."""
    if not complete_surveillance:
        raise ValueError("No-reporting is not known survival; a reporting-delay model is required")
    if quarters < 0:
        raise ValueError("Negative censor duration")
    p = model.matrix()[STATES.index(state), STATES.index(state)]
    return float(quarters * np.log(p)) if p > 0 else (-np.inf if quarters else 0.0)


def interval_endpoint_loglik(model: TransitionModel, start: str, end: str, quarters: int) -> float:
    """States observed at two endpoints; intermediate states unobserved.

    Matrix powers integrate all allowed quarterly paths, including suspensions.
    This does NOT identify the date of a first passage if re-entry is possible.
    """
    if quarters < 1:
        raise ValueError("Observation endpoints must be at least one quarter apart")
    p = np.linalg.matrix_power(model.matrix(), quarters)[STATES.index(start), STATES.index(end)]
    return float(np.log(p)) if p > 0 else -np.inf


def first_exit_interval_loglik(model: TransitionModel, state: str, destination: str,
                               lower: int, upper: int) -> float:
    """First exit occurs in integer quarters [lower, upper], no intermediate exits.

    Observation protocol must establish survival through lower-1 and the first
    exit cause; it cannot be inferred from two generic press releases.
    """
    if lower < 1 or upper < lower or destination not in ALLOWED[state]:
        raise ValueError("Invalid first-exit interval")
    matrix = model.matrix()
    stay = matrix[STATES.index(state), STATES.index(state)]
    cause = matrix[STATES.index(state), STATES.index(destination)]
    p = cause * sum(stay ** (k - 1) for k in range(lower, upper + 1))
    return float(np.log(p)) if p > 0 else -np.inf


@dataclass(frozen=True)
class FitResult:
    model: TransitionModel
    n_exposures: int
    n_exits: int
    success: bool
    objective: float
    note: str


def fit_constant_intensities(source: str, destinations: list[str], observations: list[str],
                             *, min_exits_per_parameter: int = 10, min_cause_exits: int = 5,
                             l2: float = 0.0) -> FitResult:
    """Small baseline MLE; refuse unsupported rich inference.

    Each observation is the end state after one at-risk quarter in `source`.
    Repeated project rows require clustered uncertainty outside this estimator.
    Defaults require 10 exits per coefficient and >=5 events per cause. These
    are transparent engineering guards, not universal statistical sufficiency.
    """
    if not destinations or len(set(destinations)) != len(destinations):
        raise ValueError("Distinct destination causes required")
    if any(b not in ALLOWED[source] for b in destinations):
        raise ValueError("Impossible cause")
    if any(b not in [source, *destinations] for b in observations):
        raise ValueError("Observed destination excluded from risk model")
    counts = np.array([observations.count(b) for b in destinations])
    n_exit = int(counts.sum())
    if n_exit < min_exits_per_parameter * len(destinations) or np.any(counts < min_cause_exits):
        raise ValueError("NOT_IDENTIFIABLE: too few independent observed transitions for this parameterization")
    n = len(observations)
    stay_count = n - n_exit
    if stay_count == 0 and l2 == 0:
        raise ValueError("NOT_IDENTIFIABLE: zero stay events imply no finite unpenalized intensity maximum")
    if l2 < 0:
        raise ValueError("Shrinkage penalty must be nonnegative")
    def objective(log_rates):
        probabilities = competing_probabilities(dict(zip(destinations, np.exp(log_rates))))
        ll = stay_count * np.log(probabilities["stay"])
        ll += sum(count * np.log(probabilities[b]) for b, count in zip(destinations, counts))
        return float(-ll + l2 * np.dot(log_rates, log_rates) / 2)
    initial_total = -np.log(max(stay_count / n, 1e-5))
    initial = np.log(initial_total * counts / n_exit)
    result = minimize(objective, initial, method="L-BFGS-B", bounds=[(-20, 5)] * len(destinations))
    model = TransitionModel({(source, b): float(v) for b, v in zip(destinations, np.exp(result.x))},
        provenance="estimated_constant_baseline")
    return FitResult(model, n, n_exit, bool(result.success), float(result.fun),
        "No cluster-adjusted uncertainty supplied; assess project/country/calendar dependence before inference")
