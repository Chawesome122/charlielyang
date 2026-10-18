"""Legal exposure aggregation requires frozen *observed* dependency weights."""

from __future__ import annotations

import numpy as np
import pandas as pd


def frozen_legal_exposure(rows: pd.DataFrame, *, base_year=2021):
    """Weighted ordinal legal index, never a physical access or loss fraction.

    Each row requires jurisdiction, weight, base_year, severity_ordinal, and
    source_id. Pass a single target/layer/date risk set. Absent weights cannot
    be replaced by equal shares.
    """
    required = {"jurisdiction", "weight", "base_year", "severity_ordinal", "source_id"}
    if not required.issubset(rows.columns) or rows.empty:
        raise ValueError("Missing frozen dependency data")
    if rows[list(required)].isna().any().any():
        raise ValueError("Unknown weights or severities prevent point exposure")
    if rows.jurisdiction.duplicated().any() or (rows.base_year > base_year).any():
        raise ValueError("Unique jurisdictions and pre-policy weights required")
    if not np.isfinite(rows.weight).all() or not np.isclose(rows.weight.sum(), 1.0):
        raise ValueError("Frozen dependence shares must sum to one")
    if (rows.weight < 0).any() or not rows.severity_ordinal.isin([0, .25, .5, .75, 1]).all():
        raise ValueError("Invalid weight or unregistered ordinal severity")
    return float((rows.weight * rows.severity_ordinal).sum())
