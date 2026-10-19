#!/usr/bin/env python3
"""Validate additional downstream project and finite-batch disclosure evidence.

Counterparty statements retain their role and conservative public clocks. An
issuer's batch qualification claim never becomes a stable commercial flow.
"""
import json
import math
from pathlib import Path
import re
import subprocess

import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text
from weaponized.io.schemas import Claim
from weaponized.rare_earths.materials import reported_batch_summary

ROOT = Path(__file__).resolve().parents[1]


def build():
    source_index = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").fillna("").to_dict("records"):
        source_index[row["source_id"]] = row
    specifications = json.loads((ROOT/"codebooks/industrial_evidence.json").read_text())
    checked_sources, project_rows, claims = {}, [], []

    def evidence(spec):
        sid = spec["source_id"]
        source = source_index[sid]
        if sid not in checked_sources:
            if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
                raise ValueError(f"Source hash mismatch: {sid}")
            public = source.get("publication_date")
            if not public or public > "2026-10-11":
                raise ValueError(f"Unverified/post-freeze source clock: {sid}")
            checked_sources[sid] = source
        if spec.get("pdf_page"):
            extracted = verified_original_text(ROOT/source["archive_path"], source["sha256"])
            text = extracted.split("\f")[spec["pdf_page"]-1]
            locator = f"PDF page {spec['pdf_page']}"
        else:
            text = verified_original_text(ROOT/source["archive_path"], source["sha256"])
            locator = spec["locator"]
        normalized = " ".join(text.split())
        match = re.search(spec["pattern"], normalized, re.I)
        if not match:
            raise ValueError(f"Claim quote missing: {spec['record_id']}")
        number = spec.get("capacity_native", spec.get("value"))
        if isinstance(number, (int, float)):
            numbers = [float(x.replace(",", "")) for x in re.findall(r"(?<![\d.])\d[\d,]*(?:\.\d+)?(?![\d.])", match[0])]
            if not math.isfinite(number) or number not in numbers:
                raise ValueError(f"Numerical amount not supported by extracted quote: {spec['record_id']}")
        return source, match[0], locator

    for spec in specifications["project_milestones"]:
        source, quote, locator = evidence(spec)
        public = source["publication_date"]
        upper = spec.get("event_date_upper")
        valid = upper or public
        if valid > public:
            raise ValueError("Observed milestone cannot be dated after its public source")
        lower = spec.get("event_date_lower")
        project_rows.append(dict(
            record_id=spec["record_id"], project_id=spec["project_id"], activity_id=spec["activity_id"],
            site_country=spec["site_country"], owner_parent=spec["owner_parent"],
            control_group_uncertainty="ultimate control and transaction completion not independently adjudicated",
            stage=spec["stage"], state=spec["state"],
            state_evidence=f"{spec['evidence_role']}; independent stable qualification not verified",
            event_date_lower=lower, event_date_upper=upper, exact_event_date=lower if lower and lower == upper else None,
            valid_date=valid, info_public_date=public,
            date_precision="interval" if lower else "source-date snapshot; state-entry time unknown",
            first_public_date_verified=False, publication_basis="conservative archived filing/issuer-index availability",
            capacity_native=spec.get("capacity_native"), native_unit=spec.get("native_unit"),
            product_form=spec["product_form"], feedstock_origin=spec["feedstock_origin"],
            financing=spec["financing"], routes="contractual/technical route evidence incomplete",
            process_yield="not observed", utilization="not inferred from nameplate",
            source_id=spec["source_id"], source_sha256=source["sha256"], locator=locator, quote=quote,
            eligible_for_asof=True, commercial_network_ready=False,
            cancelled_projects_coverage="selected discovery addition; population eligibility and failures remain incomplete",
            evidence_role=spec["evidence_role"], interpretation=spec["interpretation"],
            target_commission_native=spec.get("target_commission_native")))
    for spec in specifications["technical_claims"]:
        source, quote, locator = evidence(spec)
        item = dict(observation_id=spec["record_id"], record_version_id=spec["record_id"]+"-v1",
                    entity_id=spec["entity_id"], variable=spec["variable"], value=spec["value"],
                    native_unit=spec["native_unit"], product_basis=spec["product_basis"],
                    valid_date=spec.get("valid_date") or source["publication_date"],
                    info_public_date=source["publication_date"], source_id=spec["source_id"],
                    source_sha256=source["sha256"], locator=locator, evidence_class="empirical", event_kind="observed")
        Claim(**item)
        claims.append(item | dict(quote=quote, evidence_role=spec["evidence_role"], interpretation=spec["interpretation"],
                                 value_type="number" if isinstance(spec["value"], (int, float)) else "category",
                                 date_precision="reported earlier announcement; production interval unknown" if spec.get("valid_date") else "source-date snapshot; event time unknown"))
    output = ROOT/"data/processed/industrial_evidence"
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(project_rows).to_csv(output/"project_milestones.csv", index=False)
    pd.DataFrame(claims).to_csv(output/"technical_claims.csv", index=False)
    batch = {r["variable"]:r for r in claims if r["entity_id"] == "EF_KOR_finite_batch"}
    amounts = reported_batch_summary(batch["reported_oxide_input"]["value"], batch["reported_magnet_output"]["value"])
    amounts.update(source_id=batch["reported_oxide_input"]["source_id"],
                   source_sha256=batch["reported_oxide_input"]["source_sha256"],
                   info_public_date=batch["reported_oxide_input"]["info_public_date"],
                   evidence_class="empirical_issuer_reported_finite_batch",
                   claimed_earlier_announcement="2025-09-09; original release not archived here",
                   known_NdPr_feed_origin="Florida and Georgia monazite, according to filing",
                   processor="unnamed South Korean counterparty; not equated with ASM KMP",
                   qualification="issuer reports automotive QA/QC; independent customer verification unavailable",
                   amount_precision="approximately reported quantities; measurement-error distribution unavailable",
                   inventory_treatment="historical consumed batch is not a future opening stock or replenishable feed",
                   missing_inputs=["batch start/end production dates", "Nd/Pr composition and process recoveries", "other rare-earth and non-REE inputs/origins", "named processor and line capacity", "stable repeated qualified throughput", "final-grade bloc demand"])
    (ROOT/"outputs/empirical/rare_earths/finite_batch_evidence.json").write_text(json.dumps(amounts, indent=2))
    validation = dict(passed=True, project_records=len(project_rows), additional_activities=len({r["activity_id"] for r in project_rows}),
                      project_parents=len({r["project_id"] for r in project_rows}), technical_claims=len(claims),
                      checked_sources=len(checked_sources), empirical_service_identified=False,
                      statistical_risk_set_complete=False, independent_qualification_verified=False)
    (ROOT/"outputs/diagnostics/industrial_evidence_validation.json").write_text(json.dumps(validation, indent=2))
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    build()
