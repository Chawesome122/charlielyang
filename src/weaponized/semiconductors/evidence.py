"""Missing evidence stays missing; only fixed, approved targets support scores."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .access import effective_availability, strict_bottleneck, soft_minimum

LAYERS = ["eda", "lithography", "deposition_etch_implant", "metrology_clean_control", "foundry_integration", "hbm", "advanced_packaging"]
EVIDENCE_COLUMNS = ["record_id", "layer", "target_version", "channel", "score", "lower", "upper", "event_date", "info_public_date", "source_id", "source_verified", "coder", "confidence", "evidence_memo"]


@dataclass
class StatePosterior:
    layers: pd.DataFrame
    aggregate: dict
    diagnostics: dict


def estimate_semiconductor_states(evidence, rule_panel, target_version, measurement_config):
    """Versioned adjudication output, not an unsupported statistical posterior.

    The contract name 'StatePosterior' follows §11; this deterministic evidence
    ledger has no Bayesian likelihood and produces no credible intervals.
    lower/upper are evidence bounds, not confidence intervals. Rules are kept
    as a separate diagnostic and are never substituted for an access score.
    """
    config = measurement_config
    essential = config.get("essential_layers", LAYERS)
    if not essential or len(essential) != len(set(essential)) or not set(essential).issubset(LAYERS):
        raise ValueError("Register a unique nonempty subset of the seven technology layers")
    if set(EVIDENCE_COLUMNS) - set(evidence.columns):
        raise ValueError("Missing evidence schema columns")
    if evidence.record_id.duplicated().any():
        raise ValueError("Duplicate evidence record ID")
    if not evidence.empty:
        if not evidence.channel.isin(["z", "f"]).all() or not evidence.layer.isin(LAYERS).all():
            raise ValueError("Evidence channel must be domestic z or foreign f")
        for c in ["score", "lower", "upper"]:
            nums = evidence[c].dropna().astype(float)
            if ((nums < 0) | (nums > 1)).any() or not np.isfinite(nums).all():
                raise ValueError("Evidence scores and bounds must be in [0,1]")
        if ((evidence.lower > evidence.upper) | (evidence.score < evidence.lower) | (evidence.score > evidence.upper)).any():
            raise ValueError("Inconsistent capability/access evidence bounds")
        if evidence.info_public_date.isna().any() or evidence.event_date.isna().any():
            raise ValueError("Both public and event clocks required for scored evidence")
    asof = pd.Timestamp(config["as_of"])
    available = evidence.loc[
        (pd.to_datetime(evidence.info_public_date) <= asof)
        & (pd.to_datetime(evidence.event_date) <= asof)
        & evidence.target_version.eq(target_version)
        & evidence.source_verified.eq(True)
    ].copy()
    if not config.get("target_expert_approved", False):
        available = available.iloc[:0]
    # Coders are not averaged blindly. Each selected score needs a unique
    # adjudicated record; disagreement is preserved and blocks that channel.
    records, conflicts = [], []
    for layer in essential:
        row = {"layer": layer, "target_version": target_version, "as_of": str(asof.date())}
        for channel in ["z", "f"]:
            selected = available.loc[available.layer.eq(layer) & available.channel.eq(channel)].copy()
            if not selected.empty:
                selected = selected.loc[pd.to_datetime(selected.event_date) == pd.to_datetime(selected.event_date).max()]
                selected = selected.loc[pd.to_datetime(selected.info_public_date) == pd.to_datetime(selected.info_public_date).max()]
            if len(selected) == 1:
                rec = selected.iloc[0]
                row[channel] = float(rec.score) if pd.notna(rec.score) else np.nan
                row[channel + "_lower"] = float(rec.lower) if pd.notna(rec.lower) else 0.0
                row[channel + "_upper"] = float(rec.upper) if pd.notna(rec.upper) else 1.0
                row[channel + "_source_id"] = rec.source_id
                row[channel + "_status"] = "adjudicated_evidence"
            else:
                row.update({channel: np.nan, channel + "_lower": 0.0, channel + "_upper": 1.0, channel + "_source_id": None,
                            channel + "_status": "coder_conflict" if len(selected) > 1 else "unverified"})
                if len(selected) > 1:
                    conflicts.append(f"{layer}:{channel}")
        for assumption in ["residual_gap", "complementary"]:
            name = "a_" + assumption
            row[name] = float(effective_availability(row["z"], row["f"], assumption=assumption))
            row[name + "_lower"] = float(effective_availability(row["z_lower"], row["f_lower"], assumption=assumption))
            row[name + "_upper"] = float(effective_availability(row["z_upper"], row["f_upper"], assumption=assumption))
        records.append(row)
    layers = pd.DataFrame(records)
    aggregate = {"domestic_strict_min": strict_bottleneck(layers.z),
                 "effective_residual_gap_strict_min": strict_bottleneck(layers.a_residual_gap),
                 "effective_complementary_strict_min": strict_bottleneck(layers.a_complementary),
                 "domestic_soft_min_sensitivity": soft_minimum(layers.z, temperature=config.get("soft_min_temperature", .05)),
                 "domestic_lower": float(layers.z_lower.min()), "domestic_upper": float(layers.z_upper.min()),
                 "bound_type": "evidence_or_logical_bounds_not_confidence_intervals"}
    diagnostics = {"target_expert_approved": bool(config.get("target_expert_approved", False)), "input_evidence_rows": len(evidence),
                   "eligible_evidence_rows": len(available), "unknown_domestic_layers": int(layers.z.isna().sum()),
                   "unknown_foreign_layers": int(layers.f.isna().sum()), "coder_conflicts": conflicts,
                   "legal_records_separate_from_access": len(rule_panel), "causal_effect_estimated": False,
                   "game_x_available": bool(pd.notna(aggregate["domestic_strict_min"]))}
    return StatePosterior(layers, aggregate, diagnostics)
