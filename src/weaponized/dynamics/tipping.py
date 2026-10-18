"""Normalized logistic feedback: valid folds, roots and beta=4 degeneracy."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit, logit


@dataclass(frozen=True)
class FixedPoint:
    state: float
    eigenvalue: float
    stability: str
    residual: float


def rhs(t: float, z: float, theta: float, beta: float, kappa: float = 1.) -> float:
    if not all(math.isfinite(v) for v in (theta, beta, kappa)) or kappa <= 0:
        raise ValueError("Finite theta/beta and positive kappa required")
    return float(kappa * (expit(theta + beta * z) - z))


def fold_coordinates(beta: float) -> list[dict]:
    if not math.isfinite(beta):
        raise ValueError("Finite beta required")
    if beta <= 4:
        return []  # beta=4 is a degenerate cusp, not two saddle-node folds.
    root = math.sqrt(1 - 4 / beta)
    return [{"state": z, "theta": float(logit(z) - beta * z),
             "second_state_derivative": beta * (1 - 2 * z)}
            for z in ((1 - root) / 2, (1 + root) / 2)]


def fixed_points(theta: float, beta: float, kappa: float = 1., tol: float = 1e-11) -> list[FixedPoint]:
    if not all(math.isfinite(v) for v in (theta, beta, kappa)) or kappa <= 0:
        raise ValueError("Finite theta/beta and positive kappa required")
    # In log-odds coordinates roots are finite even near state boundaries.
    lo, hi = min(theta, theta + beta) - 1., max(theta, theta + beta) + 1.
    breaks = [lo] + sorted(float(logit(f["state"])) for f in fold_coordinates(beta)
                           if lo < float(logit(f["state"])) < hi) + [hi]
    f = lambda w: w - beta * expit(w) - theta
    roots = []
    for a, b in zip(breaks[:-1], breaks[1:]):
        if abs(f(a)) <= tol:
            roots.append(a)
        if f(a) * f(b) < 0:
            roots.append(brentq(f, a, b, xtol=1e-14))
        if abs(f(b)) <= tol:
            roots.append(b)
    states = sorted(float(expit(w)) for w in roots)
    unique = []
    for z in states:
        if not unique or abs(unique[-1] - z) > 1e-8:
            unique.append(z)
    result = []
    for z in unique:
        eigen = kappa * (beta * z * (1 - z) - 1)
        if abs(beta - 4) < tol and abs(theta + 2) < tol:
            stability = "nonhyperbolic_asymptotically_stable_cubic"
        elif abs(eigen) < 1e-8:
            stability = "nonhyperbolic_fold_semistable"
        else:
            stability = "asymptotically_stable" if eigen < 0 else "unstable"
        result.append(FixedPoint(z, eigen, stability, rhs(0, z, theta, beta, kappa)))
    return result


def three_root_region(beta: float) -> tuple[float, float] | None:
    folds = fold_coordinates(beta)
    return tuple(sorted(f["theta"] for f in folds)) if folds else None
