"""Bounded physical-proxy ODE and its exact constant-effort solution."""
from __future__ import annotations
import math
import numpy as np


def _validate(eta: float, effort: float, delta: float):
    if not all(math.isfinite(v) for v in (eta, effort, delta)) or eta <= 0 or effort < 0 or delta < 0:
        raise ValueError("eta > 0, effort >= 0, delta >= 0, all finite")


def rhs(t: float, r: float, eta: float, effort: float, delta: float) -> float:
    _validate(eta, effort, delta)
    return eta * effort * (1 - r) - delta * r


def steady_state(eta: float, effort: float, delta: float) -> dict:
    _validate(eta, effort, delta)
    growth = eta * effort
    rate = growth + delta
    if rate == 0:
        return {"state": None, "eigenvalue": 0., "stability": "continuum_of_neutral_equilibria"}
    return {"state": growth / rate, "eigenvalue": -rate, "stability": "globally_asymptotically_stable"}


def trajectory(time, initial: float, eta: float, effort: float, delta: float):
    _validate(eta, effort, delta)
    time = np.asarray(time, dtype=float)
    if not math.isfinite(initial) or not 0 <= initial <= 1 or np.any(~np.isfinite(time)) or np.any(time < 0):
        raise ValueError("Initial state in [0,1] and finite nonnegative times required")
    rate = eta * effort + delta
    if rate == 0:
        return np.full_like(time, initial)
    equilibrium = eta * effort / rate
    return equilibrium + (initial - equilibrium) * np.exp(-rate * time)


def critical_effort(threshold: float, eta: float, delta: float) -> float:
    _validate(eta, 0., delta)
    if not 0 < threshold < 1:
        raise ValueError("Critical-effort expression requires threshold strictly between zero and one")
    return delta * threshold / (eta * (1 - threshold))


def crossing_time(initial: float, threshold: float, eta: float, effort: float, delta: float) -> float:
    """First finite upward threshold time; infinity covers asymptotic equality.

    Initial states at/above the target return zero (already adequate), without
    asserting subsequent persistence. Exactly 100% is unreachable in finite time
    from below under this continuous proxy even though a flow LP may serve 100%.
    """
    _validate(eta, effort, delta)
    if not 0 <= initial <= 1 or not 0 < threshold <= 1:
        raise ValueError("Initial in [0,1], threshold in (0,1]")
    if initial >= threshold:
        return 0.
    rate = eta * effort + delta
    if rate == 0:
        return math.inf
    eq = eta * effort / rate
    if eq <= threshold:
        return math.inf
    return math.log((eq - initial) / (eq - threshold)) / rate
