"""Quarterly usable production-capacity envelopes, never unconstrained supply."""
from dataclasses import dataclass
from typing import Mapping
import numpy as np


@dataclass(frozen=True)
class RampSpec:
    annual_capacity: float
    utilization: float = 1.0
    kind: str = "exponential"
    speed_per_quarter: float = 0.5
    initial_age_offset: float = 0.0
    logistic_midpoint_quarters: float = 4.0
    observed_fraction: Mapping[int, float] | None = None
    capacity_unit: str = "t/year"

    def __post_init__(self):
        if self.capacity_unit != "t/year":
            raise ValueError("Convert and document native capacity units before applying a ramp")
        if self.annual_capacity < 0 or not np.isfinite(self.annual_capacity):
            raise ValueError("Capacity must be finite and nonnegative")
        if not 0 <= self.utilization <= 1 or self.speed_per_quarter <= 0 or self.initial_age_offset < 0:
            raise ValueError("Invalid utilization, speed or offset")
        if self.kind not in {"step", "exponential", "logistic", "observed"}:
            raise ValueError("Unknown ramp class")

    def output_capacity(self, quarter: int, commissioning_quarter: int | None,
                        operational: bool = True) -> float:
        if not operational or commissioning_quarter is None or quarter < commissioning_quarter:
            return 0.0
        age = quarter - commissioning_quarter
        shifted_age = age + self.initial_age_offset
        if self.kind == "step":
            fraction = 1.0
        elif self.kind == "exponential":
            fraction = -np.expm1(-self.speed_per_quarter * shifted_age)
        elif self.kind == "logistic":
            fraction = 1 / (1 + np.exp(-self.speed_per_quarter * (shifted_age - self.logistic_midpoint_quarters)))
        else:
            if self.observed_fraction is None or age not in self.observed_fraction:
                raise ValueError("No observed ramp value; extrapolation requires a registered separate model")
            fraction = self.observed_fraction[age]
        if not np.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("Invalid ramp fraction")
        return float(self.annual_capacity / 4 * self.utilization * fraction)
