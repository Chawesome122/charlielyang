#!/usr/bin/env python3
"""Validate dated milestone claims and quarterly production against archived PDFs.

Reported first production remains commissioning evidence. No stable-qualified
throughput, physical route capacity or representative hazard risk set is inferred.
"""
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.rare_earths.reported_output import parse_lynas_quarterly_front_page

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/processed/rare_earths_additional"


def build():
    sources = pd.read_csv(ROOT / "metadata/additional_rare_earth_sources.csv").fillna("").set_index("source_id")
    milestones = pd.read_csv(ROOT / "codebooks/lynas_project_milestones.csv").fillna("")
    rows, pages_cache, checked = [], {}, set()

    def pages(source_id):
        if source_id not in pages_cache:
            source = sources.loc[source_id]
            path = ROOT / source.archive_path
            if sha256_file(path) != source.sha256:
                raise ValueError(f"Source checksum mismatch: {source_id}")
            if not source.publication_date or source.publication_date > "2026-10-11":
                raise ValueError(f"Missing/post-freeze public clock: {source_id}")
            pages_cache[source_id] = path.with_suffix(".extracted.txt").read_text().split("\f")
            checked.add(source_id)
        return pages_cache[source_id]

    for item in milestones.to_dict("records"):
        source = sources.loc[item["source_id"]]
        page_number = int(item["pdf_page"])
        page = " ".join(pages(item["source_id"])[page_number - 1].split())
        match = re.search(item["evidence_pattern"], page, re.I)
        if not match:
            raise ValueError(f"Evidence not found on specified PDF page: {item['claim_id']}")
        if item["valid_date"] > source.publication_date:
            raise ValueError("An observed milestone cannot postdate its source")
        target_quote = ""
        if item["target_date_lower"] or item["target_date_upper"]:
            target_match = re.search(item["target_evidence_pattern"], page, re.I) if item["target_evidence_pattern"] else None
            if not target_match:
                raise ValueError(f"Target-date evidence missing: {item['claim_id']}")
            target_quote = target_match[0]
        rows.append(item | dict(info_public_date=source.publication_date,
                               publication_basis=source.publication_date_basis,
                               source_sha256=source.sha256, quote=match[0],
                               target_quote=target_quote,
                               locator=f"PDF page {page_number}",
                               first_public_date_verified=False,
                               evidence_class="empirical_issuer_reported",
                               stable_qualified_operation_verified=False,
                               statistical_risk_set_admissible=False))
    history = pd.DataFrame(rows)
    history.to_csv(TARGET / "lynas_project_history.csv", index=False)
    links = []
    for claim, start, finish, commodity in [
        ("LYH-005", "Lynas_MtWeld", "Lynas_Kalgoorlie", "rare-earth concentrate"),
        ("LYH-006", "Lynas_Kalgoorlie", "Lynas_Malaysia", "mixed rare-earth carbonate"),
    ]:
        row = history[history.claim_id.eq(claim)].iloc[0]
        links.append(dict(route_id=claim + "-LINK", from_node=start, to_node=finish,
                          commodity=commodity, observed_event=row.milestone,
                          event_date_lower=row.event_date_lower, event_date_upper=row.event_date_upper,
                          info_public_date=row.info_public_date, source_id=row.source_id,
                          source_sha256=row.source_sha256, locator=row.locator, quote=row.quote,
                          route_capacity_native=None, recovery_yield=None,
                          china_free_all_inputs_verified=False, commercial_network_ready=False))
    pd.DataFrame(links).to_csv(TARGET / "lynas_documented_material_links.csv", index=False)

    quarterly = []
    for sid, source in sources.iterrows():
        if source.title != "Quarterly Activities Report":
            continue
        for i, row in enumerate(parse_lynas_quarterly_front_page(pages(sid)[0])):
            quarterly.append(row | dict(observation_id=f"{sid}-QKPI-{i}",
                                        info_public_date=source.publication_date,
                                        source_id=sid, source_sha256=source.sha256,
                                        issuer="Lynas Rare Earths Ltd", facility_id="LYNAS-MALAYSIA",
                                        evidence_class="empirical_issuer_reported"))
    quarter = pd.DataFrame(quarterly).sort_values(["period_end", "product_basis", "info_public_date"])
    quarter.to_csv(TARGET / "lynas_quarterly_production_versions.csv", index=False)
    latest = quarter.drop_duplicates(["period_end", "product_basis"], keep="last")
    latest.to_csv(TARGET / "lynas_quarterly_production_asof_freeze.csv", index=False)
    annual = pd.read_csv(TARGET / "lynas_annual_production.csv")
    checks = []
    for year in sorted({int(x[:4]) + (int(x[5:7]) > 6) for x in latest.period_end}):
        group = latest[latest.period_end.gt(f"{year-1}-06-30") & latest.period_end.le(f"{year}-06-30")]
        if group.period_end.nunique() != 4:
            continue
        for product, sub in group.groupby("product_basis"):
            total = int(sub.value.sum())
            original = annual[annual.period_end.eq(f"{year}-06-30") & annual.product_basis.eq(product)]
            if len(original) != 1:
                raise ValueError("Annual reconciliation requires one own-year source")
            observed = int(original.iloc[0].value)
            checks.append(dict(fiscal_year=year, product_basis=product,
                               quarterly_sum=total, annual_report_value=observed,
                               difference=total-observed, passed=(total == observed)))
    pd.DataFrame(checks).to_csv(TARGET / "lynas_quarterly_annual_reconciliation.csv", index=False)
    if not all(row["passed"] for row in checks):
        raise ValueError("Quarterly/annual mismatch requires explicit revision adjudication")
    result = dict(passed=True, milestone_claims=len(history), projects=int(history.project_id.nunique()),
                  activities=int(history.activity_id.nunique()), quarterly_versions=len(quarter),
                  distinct_quarterly_observations=len(latest), annual_reconciliations=checks,
                  source_pdfs_checked=len(checked), freeze="2026-10-11",
                  complete_risk_set=False, empirical_network_ready=False,
                  qualification_and_unit_conversion="not inferred from first production or oxide totals")
    (ROOT / "outputs/diagnostics/lynas_history_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "annual_reconciliations"}, indent=2))


if __name__ == "__main__":
    build()
