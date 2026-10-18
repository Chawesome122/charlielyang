"""Target-specific availability maps; neither map is an engineering identity."""

from __future__ import annotations

import numpy as np


def _bounded(value):
    array = np.asarray(value, dtype=float)
    if np.any(np.isinf(array)) or np.any((array < 0) | (array > 1)):
        raise ValueError("Capability/access values must be in [0,1] or NaN (unknown)")
    return array


def effective_availability(domestic, foreign, *, assumption="residual_gap"):
    """Combine *measured* channels; a legal restriction is not an f observation.

    Missing channel inputs stay unknown. The residual-gap approximation is
    z + (1-z)f; the complementary sensitivity is min(z,f), blueprint §6.1.
    """
    z, f = np.broadcast_arrays(_bounded(domestic), _bounded(foreign))
    if assumption == "residual_gap":
        return 1 - (1 - z) * (1 - f)
    if assumption == "complementary":
        return np.minimum(z, f)
    raise ValueError(f"Unregistered availability assumption: {assumption}")


def strict_bottleneck(layers):
    """Return literal min; unknown essential layers cannot be dropped."""
    values = _bounded(layers)
    if values.size == 0:
        raise ValueError("An architecture must have at least one essential layer")
    return float(np.min(values))


def soft_minimum(layers, *, temperature=0.05):
    """Log-sum-exp smooth minimum, shifted to reproduce equal-layer scores.

    The normalized log-mean-exp lies between min and mean. It is a sensitivity
    measure and may exceed the literal bottleneck. Unknown inputs remain NaN.
    """
    values = _bounded(layers)
    if values.size == 0 or temperature <= 0:
        raise ValueError("Positive temperature and nonempty layer set required")
    if np.any(np.isnan(values)):
        return float("nan")
    smallest = np.min(values)
    return float(smallest - temperature * np.log(np.mean(np.exp(-(values - smallest) / temperature))))
