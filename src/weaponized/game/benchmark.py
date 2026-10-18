"""One-sided, constant-policy benchmark. This is not an unrestricted optimum."""
import numpy as np
from scipy.optimize import brentq


def constant_control_objective(u, a=1., vulnerability=1., k=1., rho=1., b=1.):
    if min(a, k, rho, b) <= 0 or not 0 <= vulnerability <= 1:
        raise ValueError("Invalid benchmark primitives")
    u = np.asarray(u)
    return a*u*vulnerability/(rho+b*u)-k*u*u/(2*rho)


def solve_constant_control(a=1., vulnerability=1., k=1., rho=1., b=1.):
    constant_control_objective(0., a, vulnerability, k, rho, b)
    def polynomial(u):
        return k*u*(rho+b*u)**2-a*vulnerability*rho*rho
    root = 0. if vulnerability == 0 else brentq(polynomial, 0, max(1., a*vulnerability/k), xtol=1e-14)
    policy = min(1., root)
    return {"unconstrained_nonnegative_root": root, "policy": policy,
            "polynomial_residual": polynomial(root), "myopic": min(1., a*vulnerability/k),
            "objective": float(constant_control_objective(policy,a,vulnerability,k,rho,b)),
            "scope": "one_sided_constant_control_scenario"}
