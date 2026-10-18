"""Bounded reciprocal game; all default numerical parameters are scenarios."""

from .primitives import GameParameters, dynamics, fixed_control_equilibrium, payoffs
from .active_set import solve_stage_nash

__all__ = ["GameParameters", "dynamics", "fixed_control_equilibrium", "payoffs", "solve_stage_nash"]
