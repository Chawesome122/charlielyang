"""Rebuild issuer-reported KMP shipments, route episodes and information vintages."""

from datetime import date, timedelta
import json
from pathlib import Path

import pandas as pd

from weaponized.rare_earths.followup import FREEZE
from weaponized.rare_earths.kmp_shipments import difference, load_shipments, visible_plant_dispatches

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/kmp_shipments"


def main():
    sources = {row["source_id"]: row for row in json.loads(
        (ROOT / "metadata/kmp_shipments_sources.json").read_text()
    )}
    specs = json.loads((ROOT / "codebooks/kmp_shipments_claims.json").read_text())
    claims, clocks = load_shipments(ROOT, specs, sources)
    by_id = {row["claim_id"].removeprefix("KMP:"): row for row in claims}

    quarterly = visible_plant_dispatches(claims, FREEZE)
    comparisons = []
    for left, right, reason in [
        ("alloy_produced_q3_25", "alloy_dispatch_q3_25", "within_quarter_production_minus_dispatch"),
        ("metal_produced_q3_25", "metal_dispatch_q3_25", "within_quarter_production_minus_dispatch"),
        ("alloy_dispatch_q2_26", "alloy_dispatch_q1_comparative", "quarter_over_quarter_dispatch_change"),
        ("mixed_metal_dispatch_q2_26", "mixed_metal_dispatch_q1_comparative", "quarter_over_quarter_dispatch_change"),
    ]:
        comparisons.append(difference(by_id[left], by_id[right], reason=reason))

    def amount(key):
        return by_id[key]["native_quantity"]

    component_sum = amount("alloy_dispatch_q2_26") + amount("mixed_metal_dispatch_q2_26")
    if component_sum != amount("combined_dispatch_q2_26"):
        raise ValueError("Reported Q2 component figures do not reconcile")
    combined_q1 = amount("alloy_dispatch_q1_comparative") + amount("mixed_metal_dispatch_q1_comparative")
    component_change = component_sum - combined_q1
    order_change = amount("reduced_order_volume_disclosed_jul") - amount("alloy_order_disclosed_apr")

    origins = {FREEZE}
    for row in clocks.values():
        public = date.fromisoformat(row["info_public_date"])
        origins.update((public - timedelta(days=1), public))
    vintages = []
    for origin in sorted(origins):
        for key, row in sorted(visible_plant_dispatches(claims, origin).items()):
            vintages.append(dict(
                origin=origin.isoformat(), period_end=key[0], product_form=key[1],
                selected_claim=row["claim_id"], selected_public_date=row["info_public_date"],
                native_quantity=row["native_quantity"], native_unit=row["native_unit"],
            ))

    routes = []
    for episode, key in [
        ("noveon_2025_june_alloy", "noveon_q2_25"),
        ("vac_2025_june_alloy", "vac_dispatch_q2_25"),
        ("vac_2025_june_alloy", "vac_receipt_q3_25"),
        ("usare_2025_q2_sample", "usare_sample_q2_25"),
        ("gkn_2025_june_sample", "gkn_sample_q2_25"),
        ("magnequench_2025_completed_metal_order", "magnequench_order_completed"),
        ("neo_2025_q3_hre_shipment", "narva_tb_dispatch"),
        ("neo_2025_q3_hre_shipment", "narva_dy_dispatch"),
        ("neo_2025_december_dy_delivery", "neo_dy_delivery_q4_25"),
    ]:
        row = by_id[key]
        fields = ("claim_id", "counterparty_or_scope", "product_form", "evidence_role",
                  "event_date_lower", "event_date_upper", "info_public_date", "native_quantity", "native_unit")
        routes.append({k: row[k] for k in fields} | dict(
            episode_id=episode, supplier="Korean Metals Plant", lot_level_input_origin=None,
            steady_route_capacity=None, finished_magnet_delivery=None,
        ))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in [
        ("source_clocks", list(clocks.values())), ("claims", claims),
        ("dispatch_asof_freeze", list(quarterly.values())), ("origin_replay", vintages),
        ("native_comparisons", comparisons), ("route_episodes", routes),
    ]:
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)

    alloy = "NdFeB_strip_alloy"
    mixed = "Nd_and_NdPr_metal"
    exhibit = [
        r"\begin{tabular}{lrr}",
        r"\toprule Quarter & NdFeB strip alloy & Nd plus NdPr metal \\",
        r"\midrule",
    ]
    for label, end in (
        ("2025 Q3", "2025-09-30"), ("2025 Q4", "2025-12-31"),
        ("2026 Q1", "2026-03-31"), ("2026 Q2", "2026-06-30"),
    ):
        cells = []
        for product in (alloy, mixed):
            row = quarterly.get((end, product))
            cells.append((
                (r"$\sim$" if row["source_marks_approximate"] else "") + str(row["native_quantity"])
            ) if row else "--")
        exhibit.append(" & ".join([label, *cells]) + r" \\")
    exhibit.extend([r"\bottomrule", r"\end{tabular}"])
    (ROOT / "manuscript/kmp_shipments_table.tex").write_text("\n".join(exhibit) + "\n")

    result = dict(
        passed=True, source_quarterly_reports=len(sources), source_claims=len(claims),
        native_comparisons=len(comparisons), information_origins=len(origins), origin_replay_rows=len(vintages),
        named_route_observations=len(routes), distinct_route_episodes=len({r["episode_id"] for r in routes}),
        q2_component_total_tonnes=str(component_sum), q1_comparative_sum_tonnes=str(combined_q1),
        qoq_aggregate_difference_tonnes=str(component_change),
        qoq_source_reported_difference_native_token=by_id["reported_dispatch_change_q2_26"]["native_quantity_token"],
        alloy_order_calendar_scope_change_tonnes=str(order_change),
        empirical_service_identified=False, linked_input_lots_identified=False,
        opening_stock_admitted=False, operating_recovery_identified=False,
        stable_route_capacity_identified=False, representative_first_exit_identified=False,
    )
    (ROOT / "outputs/diagnostics/kmp_shipments_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
