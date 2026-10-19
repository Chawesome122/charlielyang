#!/usr/bin/env python3
"""Fresh-original extraction of conditional concentrate engineering inputs."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

from bs4 import BeautifulSoup
import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.io.schemas import Claim
from weaponized.rare_earths.engineering import grouped_oxide_constraint, normalized_finite_feed_check

ROOT = Path(__file__).resolve().parents[1]


def numerical_value(spec: dict, quote: str) -> float:
    """Bind a value to its named product/denominator, not any nearby number."""
    variable = spec["variable"]
    number = r"(\d+(?:\.\d+)?)"
    if variable == "concentrate_TREO_grade":
        pattern = r"concentrate containing on average " + number + r"% TREO"
    elif variable in {"concentrate_REO_distribution", "separation_recovery"}:
        pattern = re.escape(spec["product_basis"]) + r" \(" + number + r"%\)"
    else:
        raise ValueError("Unregistered numerical engineering variable")
    match = re.search(pattern,quote)
    if not match:
        raise ValueError("Named numerical engineering quantity absent")
    return float(match[1])


def original_evidence(spec: dict, sources: dict, cache: dict) -> tuple[dict, str, int]:
    """Hash and reparse original HTML. Never load a derived text aid."""
    sid = spec["source_id"]
    source = sources[sid]
    if sid not in cache:
        original = ROOT/source["archive_path"]
        if sha256_file(original) != source["sha256"]:
            raise ValueError(f"Original-source checksum mismatch: {sid}")
        if not source.get("publication_date") or source["publication_date"] > "2026-10-11":
            raise ValueError(f"Unverified/post-freeze source public clock: {sid}")
        if original.suffix != ".html":
            raise ValueError("Engineering extraction currently supports original HTML only")
        cache[sid] = " ".join(BeautifulSoup(original.read_text(), "html.parser").get_text(" ", strip=True).split())
    matches = list(re.finditer(spec["pattern"], cache[sid]))
    ordinal = spec["match_ordinal"]
    if ordinal < 0 or ordinal >= len(matches):
        raise ValueError(f"Original engineering quote absent: {spec['claim_id']}")
    match = matches[ordinal]
    context = spec["engineering_context"]
    if context in {"resource_pit_optimization", "reserve_pit_optimization"}:
        headings=list(re.finditer(r"Mineral (Resources|Reserves) As of December 31, \d{4}, SRK",cache[sid][:match.start()]))
        expected="Resources" if context == "resource_pit_optimization" else "Reserves"
        if not headings or headings[-1][1] != expected:
            raise ValueError("Engineering quote belongs to the wrong resource/reserve section")
    value = spec["value"]
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or numerical_value(spec,match[0]) != value:
            raise ValueError(f"Engineering numerical value unsupported: {spec['claim_id']}")
    return source, match[0], len(matches)


def build() -> dict:
    specifications = json.loads((ROOT/"codebooks/engineering_inputs.json").read_text())
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    cache, claims = {}, []
    for spec in specifications["claims"]:
        source, quote, match_count = original_evidence(spec, sources, cache)
        observation_id = ":".join([spec["entity_id"],spec["variable"],spec["product_basis"],spec["engineering_context"],spec["valid_date"]])
        locator = f"10-K; {spec['engineering_context']}; exact normalized original-HTML regex; match ordinal {spec['match_ordinal']}"
        row = dict(observation_id=observation_id, record_version_id=observation_id+":"+spec["source_id"],
                   entity_id=spec["entity_id"], variable=spec["variable"], value=spec["value"],
                   native_unit=spec["native_unit"], product_basis=spec["product_basis"],
                   valid_date=spec["valid_date"], info_public_date=source["publication_date"],
                   source_id=spec["source_id"], source_sha256=source["sha256"], locator=locator,
                   evidence_class=spec["evidence_class"], event_kind="observed")
        Claim(**row)
        claims.append(row | dict(claim_id=spec["claim_id"], quote=quote,
                                 engineering_context=spec["engineering_context"], classification=spec["classification"],
                                 interpretation=spec["interpretation"], source_url=source["url"],
                                 source_retrieval_timestamp=source["retrieval_timestamp"],
                                 information_basis=spec["information_basis"], historical_byte_vintage_certified=False,
                                 valid_date_basis="reporting period end; exact engineering-assumption adoption/event date unknown",
                                 source_match_count=match_count, match_ordinal=spec["match_ordinal"],
                                 actual_industrial_flow_identified=False))
    if len({r["record_version_id"] for r in claims}) != len(claims):
        raise ValueError("Duplicate engineering claim/version")
    table = pd.DataFrame(claims)
    coefficients, diagnostics = [], []
    for sid in sorted(table.source_id.unique()):
        subset = table[table.source_id == sid]
        distribution = {r["product_basis"]:float(r["value"])/100
                        for r in subset[subset.variable == "concentrate_REO_distribution"].to_dict("records")}
        for context in ["resource_pit_optimization", "reserve_pit_optimization"]:
            rows = subset[subset.engineering_context == context]
            grade = rows[rows.variable == "concentrate_TREO_grade"].iloc[0]
            recovery = rows[(rows.variable == "separation_recovery") & (rows.product_basis == "PrNd Oxide")].iloc[0]
            coefficient = grouped_oxide_constraint(float(grade.value)/100, distribution, float(recovery.value)/100,
                                                  product="PrNd", input_basis="tonne_native_concentrate",
                                                  output_basis="tonne_REO_equivalent")
            coefficient.update(source_id=sid, source_sha256=grade.source_sha256, info_public_date=grade.info_public_date,
                               engineering_context=context, classification="issuer_planning_assumption_derived_constraint",
                               source_claim_ids="|".join([grade.claim_id,recovery.claim_id]+subset[subset.variable == "concentrate_REO_distribution"].claim_id.tolist()),
                               scope="partial necessary bound; not a complete LP production activity or final demand recipe")
            coefficients.append(coefficient)
            for feed in [0., .5, 1.]:
                check=normalized_finite_feed_check(coefficient["recovered_product_REO_equivalent_per_native_tonne"], feed)
                diagnostics.append(check | dict(source_id=sid, engineering_context=context))
    # Differences between successive issuer engineering models are not operating changes.
    recoveries = table[table.variable == "separation_recovery"].copy()
    revisions = []
    for (context, product), rows in recoveries.groupby(["engineering_context", "product_basis"]):
        ordered = rows.sort_values("info_public_date")
        old, new = ordered.iloc[0], ordered.iloc[-1]
        revisions.append(dict(engineering_context=context, product_basis=product,
                              earlier_source_id=old.source_id, later_source_id=new.source_id,
                              earlier_value=float(old.value), later_value=float(new.value),
                              difference_percentage_points=float(new.value)-float(old.value),
                              classification="change_in_issuer_model_assumption_not_observed_operating_recovery",
                              earlier_source_sha256=old.source_sha256,later_source_sha256=new.source_sha256))
    out = ROOT/"data/processed/engineering_inputs"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out/"observations.csv", index=False)
    pd.DataFrame(coefficients).to_csv(out/"conditional_oxide_constraints.csv", index=False)
    pd.DataFrame(revisions).to_csv(out/"recovery_assumption_versions.csv", index=False)
    validation = dict(passed=True, original_source_files=len(cache), source_claims=len(claims),
                      numerical_claims=sum(isinstance(r["value"],(int,float)) for r in claims),
                      conditional_constraints=len(coefficients), normalized_finite_feed_LP_checks=len(diagnostics),
                      checks=diagnostics, joint_distribution_sum_checked=True,
                      resource_reserve_contexts_preserved=True, independent_operating_recovery_estimated=False,
                      annual_output_identified=False, Nd_Pr_split_identified=False,
                      Dy_Tb_flow_identified=False, China_free_service_identified=False,
                      historical_byte_vintage_certified=False, freeze=specifications["freeze"])
    (ROOT/"outputs/diagnostics/engineering_inputs_validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    print(json.dumps({k:v for k,v in validation.items() if k!="checks"},indent=2))
    return validation


if __name__ == "__main__":
    build()
