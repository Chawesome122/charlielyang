"""Extract source-vintaged White Mesa flows, stocks and conditional capacities."""
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.original_text import normalize_evidence, verified_original_text
from weaponized.io.schemas import Claim
from weaponized.rare_earths.plant_ledger import capacity_identity, opening_stock_readiness, reported_flow_ratio, reported_form_set

ROOT = Path(__file__).resolve().parents[1]

INTERPRETATION = {
    "processed_feed":"Period-processed bulk feed, not contained REO or an available opening stock.",
    "reported_production":"Native reported product or contained TREO, not an elemental recovery or qualified magnet throughput.",
    "work_in_process":"In-solution quantity; exact measurement date and chemical basis incomplete; not additive to finished product supply.",
    "separated_product_inventory":"Explicit year-end stock; current opening supply requires a dated flow bridge and verified product form.",
    "sampling_sales":"Sampling sales meeting the named recipient's applicable specifications; not universal magnet qualification or a separate additive production batch.",
    "sales_disclosure":"No rare-earth sales does not imply no production or zero inventories.",
    "shared_processing_constraint":"Uranium and monazite share the instantaneous front end; annual time sharing requires rates and schedules, not independent capacity addition.",
    "design_capacity":"Issuer design range, conditional on feed and operation; not observed throughput or a joint probability distribution.",
    "expected_capacity_table":"Conditional expected component/combined table; existing label does not verify achieved rate, and dashes are not measured zeros.",
    "production_target":"Forward target, not realized production or independent operating capability.",
    "rounded_unit_statement":"The rounded issuer glossary does not identify an exact ton standard or authorize precise conversion.",
    "reported_milestone":"Keep engineering and accounting event definitions separate; quarter enclosures are not exact dates or first-exit survival data.",
}


def verify_mass_basis(spec, match):
    """A nearby number cannot justify a different physical form or ton unit."""
    roles = {"processed_feed", "reported_production", "work_in_process", "separated_product_inventory", "sampling_sales"}
    if spec["quantity_role"] not in roles or not spec["numeric_group"]:
        return
    tail = match.string[match.end(spec["numeric_group"]):]
    expected = {"metric_tonnes":r"\s+tonnes\b", "native_tons_unspecified":r"\s+tons\b"}
    if spec["native_unit"] not in expected or not re.match(expected[spec["native_unit"]], tail):
        raise ValueError("Named mass quantity has a different native ton unit")
    for basis, phrase in [("NdPr_oxide", "tonnes of NdPr oxide"), ("NdPr_oxalate", "tonnes of NdPr oxalate"),
                          ("TREO_content_in_RECarbonate", "tonnes of TREO in the form of RE Carbonate")]:
        if spec["product_basis"] == basis and phrase not in match[0]:
            raise ValueError("The source does not support the asserted chemical/product mass basis")


def build():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    book = json.loads((ROOT/"codebooks/white_mesa.json").read_text())
    cache, rows = {}, []
    for spec in book["claims"]:
        source = sources[spec["source_id"]]
        if not source.get("publication_date") or source["publication_date"] > book["freeze"]:
            raise ValueError("Source lacks an admissible public clock")
        if spec["source_id"] not in cache:
            cache[spec["source_id"]] = normalize_evidence(verified_original_text(ROOT/source["archive_path"], source["sha256"]))
        match = re.search(spec["pattern"], cache[spec["source_id"]])
        if not match:
            raise ValueError(f"Original White Mesa evidence absent: {spec['claim_id']}")
        if spec["numeric_group"] and float(match[spec["numeric_group"]].replace(",", "")) != spec["value"]:
            raise ValueError("Named source quantity does not support the curated value")
        verify_mass_basis(spec, match)
        oid = ":".join([spec["entity_id"], spec["variable"], spec["episode_id"], spec["product_basis"], spec["valid_date"], spec.get("component", "")])
        row = {key:spec[key] for key in ["entity_id", "variable", "value", "native_unit", "product_basis", "valid_date", "event_kind"]}
        row.update(observation_id=oid, record_version_id=oid+":"+spec["source_id"], info_public_date=source["publication_date"],
                   source_id=spec["source_id"], source_sha256=source["sha256"], evidence_class="empirical",
                   locator="10-K Properties/MD&A; exact original phrase and named group in codebook")
        Claim(**row)
        row.update({key:spec.get(key) for key in ["claim_id", "episode_id", "quantity_role", "period_start", "measurement_date_known", "date_precision", "component", "event_date_lower", "event_date_upper"]})
        row.update(quote=match[0], interpretation=INTERPRETATION[spec["quantity_role"]],
                   source_url=source["url"], historical_byte_vintage_certified=False,
                   physical_qualified_supply_identified=False)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.record_version_id.duplicated().any():
        raise ValueError("Duplicate plant observation version")
    out = ROOT/"data/processed/white_mesa"
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out/"observations.csv", index=False)
    ratios = []
    paired = frame[frame.quantity_role.isin(["processed_feed", "reported_production"])]
    for (sid, episode), group in paired.groupby(["source_id", "episode_id"]):
        feed = group[group.quantity_role.eq("processed_feed")]
        output = group[group.quantity_role.eq("reported_production")]
        if len(feed) != 1 or len(output) != 1:
            continue  # Generic annual aliases are not another paired input/output batch.
        a, b = feed.iloc[0], output.iloc[0]
        ratios.append(dict(source_id=sid, source_sha256=a.source_sha256, episode_id=episode,
                           info_public_date=a.info_public_date, output_product_basis=b.product_basis,
                           feed=float(a.value), output=float(b.value),
                           **reported_flow_ratio(float(a.value), float(b.value), a.native_unit, b.native_unit)))
    pd.DataFrame(ratios).to_csv(out/"reported_flow_ratios.csv", index=False)
    stocks = frame[frame.variable.eq("reported_stock")]
    audit = []
    for origin in ["2025-12-31", "2026-02-26", "2026-06-30", book["freeze"]]:
        for row in stocks.to_dict("records"):
            audit.append(dict(origin=origin, claim_id=row["claim_id"], source_id=row["source_id"],
                              valid_date=row["valid_date"], info_public_date=row["info_public_date"],
                              **opening_stock_readiness(row, origin)))
    pd.DataFrame(audit).to_csv(out/"stock_origin_audit.csv", index=False)
    capacity = frame[frame.quantity_role.eq("expected_capacity_table")]
    identities = []
    for product, group in capacity.groupby("product_basis"):
        values = dict(zip(group.component, pd.to_numeric(group.value)))
        result = capacity_identity(values.get("p1", 0.), values["p2"], values["total"])
        if not result["passed"]:
            raise ValueError("Published capacity components do not reconcile")
        identities.append(dict(product_basis=product, source_id=group.iloc[0].source_id,
                               native_unit="native_table_tpa", dash_treatment="zero only for displayed table arithmetic; not measured production", **result))
    pd.DataFrame(identities).to_csv(out/"capacity_component_identities.csv", index=False)
    versions = frame[frame.episode_id.eq("WhiteMesa_2024_commissioning_run") & frame.variable.eq("reported_output")].to_dict("records")
    forms = [reported_form_set(versions, origin) for origin in ["2024-12-31", "2025-03-31", book["freeze"]]]
    pd.DataFrame(forms).to_csv(out/"product_form_versions.csv", index=False)
    legacy = pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv")
    affected = legacy[legacy.source_id.eq("RE-EF-10K2024") & legacy.entity_id.eq("EF_WhiteMesa_separation")]
    if len(affected) != 3 or not affected.product_basis.eq("separated_NdPr_reported_product_form_unconfirmed").all():
        raise ValueError("Legacy chemical-form coding correction is absent")
    corrected = [dict(record_version_id=r.record_version_id, source_id=r.source_id, source_sha256=r.source_sha256,
                      earlier_research_label="separated_NdPr_oxide", corrected_research_label=r.product_basis,
                      correction_type="research_coding_correction_not_issuer_revision",
                      unchanged_value=r.value, source_public_date=r.info_public_date,
                      justification="Legacy generic NdPr quote did not establish oxide mass; own-source commissioning passage states oxalate; no mass conversion authorized")
                 for r in affected.itertuples()]
    pd.DataFrame(corrected).to_csv(out/"basis_corrections.csv", index=False)
    result = dict(passed=True, source_claims=len(frame), original_sources=len(cache), paired_flow_comparisons=len(ratios),
                  unit_matched_descriptive_ratios=sum(r["reported_product_per_bulk_feed"] is not None for r in ratios),
                  stock_disclosures=len(stocks), stock_origin_checks=len(audit),
                  admissible_opening_stocks=sum(r["opening_stock_admissible"] for r in audit),
                  capacity_component_checks=len(identities), product_form_origin_checks=len(forms),
                  legacy_basis_corrections=len(corrected), chemical_recovery_estimated=False,
                  current_stock_at_freeze_identified=False, commissioning_definition_adjudicated=False,
                  new_project_hazard_spells=0, empirical_service_or_forecast_identified=False,
                  historical_byte_vintage_certified=False, freeze=book["freeze"])
    (ROOT/"outputs/diagnostics/white_mesa_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    build()
