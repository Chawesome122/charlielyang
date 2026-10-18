"""Bounded layer adaptation dynamics from blueprint §6.4, time in years."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class LayerParameters:
    kappa: float
    g: float
    eta: float
    delta: float
    alpha: float = 0.0
    theta: float = 0.0
    j_min: float = 0.0

    def __post_init__(self):
        if not all(np.isfinite(v) for v in self.__dict__.values()):
            raise ValueError("All layer parameters must be finite")
        if self.kappa <= 0 or min(self.g, self.eta, self.delta, self.j_min) < 0:
            raise ValueError("kappa > 0; g, eta, delta, j_min >= 0 required")


def effort_target(restriction, params: LayerParameters, *, exogenous_index=0.0):
    """Effort has baseline-normalized intensity units, not dollars or patents."""
    if not np.isfinite(restriction) or not 0 <= restriction <= 1:
        raise ValueError("Restriction intensity must be finite and bounded")
    if not np.isfinite(exogenous_index):
        raise ValueError("Finite exogenous index required")
    return float(params.j_min + np.logaddexp(0.0, params.alpha + params.theta * restriction + exogenous_index))


def layer_rhs(time, state, params: LayerParameters, restriction, *, exogenous_index=0.0):
    """State is (realized effort pipeline p, demonstrated capability z)."""
    p, z = state
    j = effort_target(restriction, params, exogenous_index=exogenous_index)
    return np.array([params.kappa * (j - p), (params.g + params.eta * p) * (1 - z) - params.delta * z])


def fixed_control_steady_state(params: LayerParameters, restriction, *, exogenous_index=0.0):
    p = effort_target(restriction, params, exogenous_index=exogenous_index)
    growth = params.g + params.eta * p
    denominator = growth + params.delta
    return {
        "p": p,
        "z": growth / denominator if denominator else None,
        "eigenvalues": [-params.kappa, -denominator],
        "unique_z": denominator > 0,
        "interpretation": "scenario; parameters not estimated by this function",
    }


def simulate_layer(params, restriction, *, initial=(0.0, 0.0), years=10.0, points=161):
    if not np.all(np.isfinite(initial)) or initial[0] < 0 or not 0 <= initial[1] <= 1:
        raise ValueError("Require initial p >= 0 and z in [0,1]")
    if years <= 0 or points < 2:
        raise ValueError("Positive horizon and at least two output points required")
    solution = solve_ivp(
        layer_rhs, (0.0, years), initial, args=(params, restriction),
        t_eval=np.linspace(0.0, years, points), rtol=1e-9, atol=1e-11,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    p, z = solution.y
    if p.min() < -1e-9 or z.min() < -1e-9 or z.max() > 1 + 1e-9:
        raise RuntimeError("Layer integration violated physical bounds")
    return solution
