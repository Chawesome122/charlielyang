"""Build the pre-freeze follow-up from archived primary-source snapshots."""

from datetime import date
import json
from pathlib import Path

import pandas as pd

from weaponized.rare_earths.followup import (
    FREEZE,
    capacity_cells,
    compare_capacities,
    donald_as_of,
    extract_claims,
    source_clocks,
    verified_html,
)
from weaponized.rare_earths.plant_ledger import opening_stock_readiness

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/rare_earth_followup"


def main():
    sources = {row["source_id"]: row for row in json.loads(
        (ROOT / "metadata/rare_earth_followup_sources.json").read_text()
    )}
    specs = json.loads((ROOT / "codebooks/rare_earth_followup_claims.json").read_text())
    clocks = source_clocks(ROOT, sources)
    claims, values = extract_claims(ROOT, specs, sources, clocks)
    by_id = {row["claim_id"]: row for row in claims}

    sec = sources["RE-FU-EF-Q2-HTML"]
    cells = capacity_cells(verified_html(ROOT, sec))
    for row in cells:
        row.update(
            clocks[sec["source_id"]], source_sha256=sec["sha256"], source_url=sec["source_url"],
            locator="Form 10-Q, summary of Mill's existing and planned REE circuit capacity",
        )
    capacity = compare_capacities(cells, *(
        values["FU:white_mesa_" + key] for key in (
            "march_heavy_design", "july_heavy_design", "august_heavy_design", "july_combined",
        )
    ))
    if not all(row["table_components_reconcile"] for row in capacity):
        raise ValueError("White Mesa table arithmetic does not reconcile")
    december_design = values["FU:white_mesa_dec_heavy_design"]
    for row in capacity:
        earlier = december_design.get(row["element"])
        row["december_2025_phase1_prose"] = earlier
        row["december_2025_matches_august_2026_table"] = (
            earlier == row["table_phase1"] if earlier is not None else None
        )

    prior = pd.read_csv(ROOT / "data/processed/donald/fid_target_revision.csv").iloc[0]
    targets = [
        dict(claim_id=prior[f"{version}_claim_id"],
             info_public_date=prior[f"{version}_public_by"],
             event_date_upper=prior[f"{version}_target_upper"])
        for version in ("initial", "revised")
    ] + [by_id["FU:donald_q4_target"]]
    origins = [date.fromisoformat(day) for day in (
        "2026-02-25", "2026-02-26", "2026-06-30", "2026-08-04",
        "2026-08-05", "2026-09-29", "2026-09-30", FREEZE.isoformat(),
    )]
    fid = donald_as_of(origins, targets)
    new_target = by_id["FU:donald_q4_target"]
    days_after_march = (
        date.fromisoformat(new_target["info_public_date"]) - date.fromisoformat(prior["initial_target_upper"])
    ).days

    stocks = pd.read_csv(ROOT / "data/processed/white_mesa/observations.csv", keep_default_na=False)
    stock = stocks[(stocks.quantity_role == "separated_product_inventory") & (stocks.valid_date == "2025-12-31")]
    if len(stock) != 1:
        raise ValueError("Expected dated White Mesa finished stock")
    stock_row = stock.iloc[0].to_dict()
    opening_stock = dict(
        origin=FREEZE.isoformat(), stock_claim_id=stock_row["claim_id"],
        source_id=stock_row["source_id"], source_sha256=stock_row["source_sha256"],
        **opening_stock_readiness(stock_row, FREEZE.isoformat()),
    )
    if opening_stock["opening_stock_admissible"]:
        raise ValueError("Unverified current opening stock admitted")

    rosters = []
    for claim_id, project, activity, country, owner, stage, state, evidence, form in [
        ("white_mesa_july_construction", "EF_WhiteMesa", "EF_Phase1_heavies", "USA", "Energy Fuels",
         "separation", "C", "Construction underway by release. Exact start and first exit unknown.", "planned heavy oxides"),
        ("upton_early_commissioning", "RER_UptonDemo", "RER_Upton_separation", "USA", "Rare Element Resources / General Atomics",
         "separation", "Q", "Equipment shakedown and commissioning before subsequent rework.", "demonstration NdPr oxide"),
        ("upton_initial_operations", "RER_UptonDemo", "RER_Upton_separation", "USA", "Rare Element Resources / General Atomics",
         "separation", "Q", "Initial demonstration operations before full end-to-end processing.", "demonstration NdPr oxide"),
        ("kmp_reported_operating", "ASM_KoreanMetalsPlant", "ASM_KMP_metal_alloy", "KOR",
         "Australian Strategic Materials / Energy Fuels subsidiary following August 28 closing",
         "metal_alloy", "O", "Issuer-reported existing operation and ownership. Qualified throughput unverified.", "NdFeB alloy"),
        ("donald_pre_fid_work", "EF_Donald", "EF_Donald_feed", "AUS", "Donald JV",
         "mine", "F", "Issuer reports pre-FID work; no completed FID or first exit observed.", "monazite/xenotime feed"),
    ]:
        claim = by_id["FU:" + claim_id]
        rosters.append(dict(
            record_id=claim["claim_id"], project_id=project, activity_id=activity,
            site_country=country, owner_parent=owner, stage=stage, state=state,
            control_group_uncertainty="control rights and all-input origins not fully traced",
            state_evidence=evidence, product_form=form,
            event_date_lower=claim["event_date_lower"], event_date_upper=claim["event_date_upper"],
            valid_date=claim["event_date_upper"], info_public_date=claim["info_public_date"],
            date_precision="by date; exact first entry unknown", first_public_date_verified=False,
            publication_basis=claim["publication_basis"], source_id=claim["source_id"],
            source_sha256=claim["source_sha256"], locator=claim["locator"], quote=claim["quote"],
            eligible_for_asof=True, commercial_network_ready=False,
        ))
        if claim_id == "kmp_reported_operating":
            rosters[-1].update(
                capacity_native=values["FU:kmp_existing_alloy_nameplate"]["kmp"],
                native_unit="tonnes/year reported existing NdFeB alloy nameplate",
            )


    scope_claims = {
        "white_mesa_dy_initial_customer_benchmarks": "FU:white_mesa_dy_initial_benchmarks",
        "white_mesa_tb_customer_qualification": "FU:white_mesa_tb_buyer_qualification",
        "donald_reported_us_export_approval": "FU:donald_us_reec_export_approval",
    }
    origins = ("2025-12-18", "2025-12-19", "2026-08-18", "2026-08-19", "2026-08-31",
               "2026-09-01", FREEZE.isoformat())
    permit_timeline = [
        dict(origin=origin, milestone=scope, supporting_claim=claim_id,
             claimed_by=by_id[claim_id]["info_public_date"],
             public_at_origin=by_id[claim_id]["info_public_date"] <= origin,
             verified_route_capacity=None, matched_opening_stock=None, confirmed_shipment=None)
        for origin in origins for scope, claim_id in scope_claims.items()
    ]

    audit = dict(
        qualification_and_export_origin_checks=len(permit_timeline),
        december_design_comparisons=sum(row["december_2025_phase1_prose"] is not None for row in capacity),
        dated_issuer_reported_export_approval=by_id["FU:donald_us_reec_export_approval"]["info_public_date"],
        reported_white_mesa_tb_qualification_public_by=by_id["FU:white_mesa_tb_buyer_qualification"]["info_public_date"],
        permit_instrument_archived=False, stable_qualified_throughput_identified=False,
        passed=True, source_clocks=len(clocks), source_claims=len(claims),
        capacity_native_cells=len(cells), capacity_identity_checks=len(capacity),
        capacity_printed_dashes=sum(row["displayed_dash"] for row in cells),
        capacity_nonzero_prose_table_discrepancies=sum(
            bool(row[key]) for row in capacity for key in (
                "august_phase1_prose_minus_table", "july_combined_prose_minus_august_table",
            )
        ),
        donald_vintage_checks=len(fid), donald_q4_target_first_admitted=new_target["info_public_date"],
        donald_days_from_march_deadline_to_q4_revision=days_after_march,
        acquisition_closed_as_reported="2026-08-28",
        kmp_existing_alloy_nameplate=values["FU:kmp_existing_alloy_nameplate"]["kmp"],
        kmp_planned_alloy_nameplate=values["FU:kmp_planned_alloy_nameplate"]["kmp"],
        dated_project_snapshots=len(rosters), stock_origin_checks=1,
        upton_substantial_completion_date_identified=False,
        verified_2024_white_mesa_product_mass_basis=False,
        actual_donald_fid_date_identified=False, qualified_route_capacity_identified=False,
        current_opening_stock_admitted=False, actual_recovery_estimated=False,
        empirical_service_identified=False, first_exit_spell_identified=False,
        original_at_vintage_bytes_certified=False,
    )
    DATA.mkdir(parents=True, exist_ok=True)
    for name, rows in [
        ("source_clocks", list(clocks.values())), ("claims", claims), ("capacity_native_cells", cells),
        ("capacity_comparisons", capacity), ("donald_target_vintages", fid),
        ("stock_at_freeze", [opening_stock]), ("project_snapshots", rosters),
        ("qualification_and_export_vintages", permit_timeline),
    ]:
        pd.DataFrame(rows).to_csv(DATA / f"{name}.csv", index=False)

    white_capacity = {row["element"]: row for row in capacity}
    table = [
        r"\begin{tabular}{lrrr}",
        r"\toprule Design disclosure & NdPr & Tb & Dy \\",
        r"\midrule",
        r"March Phase 1 heavy expansion prose & -- & "
        f"{white_capacity['tb']['march_phase1_prose']:,} & {white_capacity['dy']['march_phase1_prose']:,}" + r" \\",
        r"July and August Phase 1 heavy expansion prose & -- & "
        f"{white_capacity['tb']['august_phase1_prose']:,} & {white_capacity['dy']['august_phase1_prose']:,}" + r" \\",
        "August Phase 1 table & " + " & ".join(f"{row['table_phase1']:,}" for row in capacity) + r" \\",
        "August Phase 2 table & " + " & ".join(f"{row['table_phase2']:,}" for row in capacity) + r" \\",
        "August combined table & " + " & ".join(f"{row['table_total']:,}" for row in capacity) + r" \\",
        "July combined prose & " + " & ".join(f"{row['july_combined_prose']:,}" for row in capacity) + r" \\",
        r"\bottomrule",
        r"\end{tabular}",
    ]
    (ROOT / "manuscript/white_mesa_followup_table.tex").write_text("\n".join(table) + "\n")
    (ROOT / "outputs/diagnostics/rare_earth_followup_validation.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
