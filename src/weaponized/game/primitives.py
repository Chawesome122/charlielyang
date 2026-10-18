"""Blueprint 8.1–8.3, with time measured in years."""
from dataclasses import asdict, dataclass, replace
import numpy as np


@dataclass(frozen=True)
class GameParameters:
    """Hypothetical inputs, not estimated preferences or empirical calibration."""
    g_c: float = 0.12
    g_u: float = 0.10
    beta_c: float = 0.7
    beta_u: float = 0.7
    delta_c: float = 0.08
    delta_u: float = 0.07
    kappa_c: float = 0.5
    kappa_u: float = 0.5
    rho_u: float = 0.2
    rho_c: float = 0.2
    a_u: float = 0.8
    a_c: float = 0.8
    d_u: float = 0.5
    d_c: float = 0.5
    k_u: float = 1.0
    k_c: float = 1.0
    h_u: float = 0.05
    h_c: float = 0.05
    b_u: float = 0.2
    b_c: float = 0.2
    q_u: float = 0.15
    q_c: float = 0.15

    def __post_init__(self):
        values = asdict(self)
        if not all(np.isfinite(v) for v in values.values()):
            raise ValueError("Parameters must be finite")
        for name in ("g_c", "g_u", "kappa_c", "kappa_u", "rho_u", "rho_c", "k_u", "k_c"):
            if values[name] <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("delta_c", "delta_u", "a_u", "a_c", "d_u", "d_c", "h_u", "h_c", "b_u", "b_c"):
            if values[name] < 0:
                raise ValueError(f"{name} must be nonnegative")
        # beta and q are sign unrestricted. Prevent overflow on the state cube.
        if max(abs(self.beta_c), abs(self.beta_u)) > 600:
            raise ValueError("Exponential growth would be numerically unsafe")
        if not np.isfinite([self.g_c*np.exp(max(0,self.beta_c)),self.g_u*np.exp(max(0,self.beta_u))]).all():
            raise ValueError("Growth rates overflow on the state cube")

    def with_updates(self, **kwargs):
        return replace(self, **kwargs)


def dynamics(state, u, c, p: GameParameters):
    """State order (x,y,m,n), vectorized over leading dimensions."""
    s = np.asarray(state, dtype=float)
    x, y, m, n = np.moveaxis(s, -1, 0)
    gc, gu = p.g_c * np.exp(p.beta_c * m), p.g_u * np.exp(p.beta_u * n)
    return np.stack((gc * (1 - x) - p.delta_c * x,
                     gu * (1 - y) - p.delta_u * y,
                     p.kappa_c * (np.asarray(u) - m),
                     p.kappa_u * (np.asarray(c) - n)), axis=-1)


def fixed_control_equilibrium(u, c, p: GameParameters):
    if not 0 <= u <= 1 or not 0 <= c <= 1:
        raise ValueError("Controls must belong to [0,1]")
    gc, gu = p.g_c * np.exp(p.beta_c * u), p.g_u * np.exp(p.beta_u * c)
    state = np.array([gc / (gc + p.delta_c), gu / (gu + p.delta_u), u, c])
    eigenvalues = np.array([-gc - p.delta_c, -gu - p.delta_u, -p.kappa_c, -p.kappa_u])
    return state, eigenvalues


def payoffs(state, u, c, p: GameParameters):
    x, y, m, n = np.moveaxis(np.asarray(state), -1, 0)
    us = p.a_u*u*(1-x)-p.d_u*c*(1-y)-0.5*p.k_u*u*u-0.5*p.h_u*n*n+p.b_u*y+p.q_u*u*c
    cn = p.a_c*c*(1-y)-p.d_c*u*(1-x)-0.5*p.k_c*c*c-0.5*p.h_c*m*m+p.b_c*x+p.q_c*u*c
    return us, cn


def pipeline_quarter(previous, control, kappa, delta=0.25):
    """Exact pipeline update for a control constant within the quarter."""
    if kappa <= 0 or delta <= 0:
        raise ValueError("Positive adjustment and elapsed years required")
    return np.asarray(control)+(np.asarray(previous)-control)*np.exp(-kappa*delta)


def constant_pipeline_state_transition(previous, pipeline, g, beta, depreciation, delta=0.25):
    """Exact only when the pipeline is held constant; not a full coupled step."""
    if g <= 0 or depreciation < 0 or delta <= 0:
        raise ValueError("Invalid transition primitives")
    growth = g*np.exp(beta*np.asarray(pipeline))
    rate = growth+depreciation
    steady = growth/rate
    return steady+(np.asarray(previous)-steady)*np.exp(-rate*delta)
