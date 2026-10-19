"""Source-linked finance identities and feedstock-conditional product plans."""
import json
import math
import os
from pathlib import Path
import re
import subprocess

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.io.schemas import Claim
from weaponized.rare_earths.finance import cash_reconciliation, facility_reconciliation, planned_capacity_retention

ROOT = Path(__file__).resolve().parents[1]


def build():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    specs = json.loads((ROOT/"codebooks/finance_material.json").read_text())
    pages, claims = {}, []
    for spec in specs["claims"]:
        sid = spec["source_id"]
        source = sources[sid]
        if sid not in pages:
            if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
                raise ValueError("Finance/material original PDF checksum mismatch")
            if not source.get("publication_date") or source["publication_date"] > specs["freeze"]:
                raise ValueError("Finance/material source lacks an admissible public clock")
            clock = sources[source["public_clock_source_id"]]
            if sha256_file(ROOT/clock["archive_path"]) != source["public_clock_source_sha256"]:
                raise ValueError("Publication evidence checksum mismatch")
            # Re-extract from the hashed original, rather than trust a text aid.
            text = subprocess.check_output(["pdftotext", "-layout", str(ROOT/source["archive_path"]), "-"], text=True)
            pages[sid] = [" ".join(page.split()) for page in text.split("\f")]
        page = pages[sid][spec["pdf_page"]-1]
        match = re.search(spec["pattern"], page)
        if not match:
            raise ValueError(f"Original PDF quote absent: {spec['claim_id']}")
        value = spec["value"]
        if isinstance(value, (int, float)):
            numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", match[0])]
            word = spec.get("numeric_word")
            word_support = word == "four" and value == 4 and re.search(r"\bfour\b", match[0])
            if not math.isfinite(value) or (abs(value) not in numbers and not word_support):
                raise ValueError("Numerical finance/material claim lacks quoted support")
        if sid == "RE-ILUKA-HALF2026" and "All currencies shown in this report are Australian dollars unless otherwise indicated." not in pages[sid][2]:
            raise ValueError("Iluka AUD unit convention absent")
        if sid == "RE-PENSANA-INTERIM-PDF" and spec["quantity_role"] == "reported_cashflow_reconciliation" and "US$ US$" not in page:
            raise ValueError("Pensana signed reconciliation USD header absent")
        observation = ":".join([spec["entity_id"], spec["variable"], spec["valid_date"], spec["product_basis"], spec.get("feed_case") or ""])
        row = dict(observation_id=observation, record_version_id=observation+":"+sid,
                   entity_id=spec["entity_id"], variable=spec["variable"], value=value,
                   native_unit=spec["native_unit"], product_basis=spec["product_basis"],
                   valid_date=spec["valid_date"], info_public_date=source["publication_date"],
                   source_id=sid, source_sha256=source["sha256"], locator=f"PDF page {spec['pdf_page']}; exact quote/regex in curated codebook",
                   evidence_class="empirical", event_kind=spec["event_kind"])
        Claim(**row)
        claims.append(row | dict(claim_id=spec["claim_id"], period_start=spec.get("period_start"),
                                 pdf_page=spec["pdf_page"], quote=match[0], quantity_role=spec["quantity_role"],
                                 feed_case=spec.get("feed_case"), interpretation=spec["interpretation"],
                                 value_type="number" if isinstance(value, (int, float)) else "category",
                                 public_clock_source_id=source["public_clock_source_id"],
                                 public_clock_source_sha256=source["public_clock_source_sha256"],
                                 historical_byte_vintage_certified=False,
                                 independent_corroboration=False))
    frame = pd.DataFrame(claims)
    if frame.record_version_id.duplicated().any():
        raise ValueError("Duplicate finance/material observation version")
    out = ROOT/"data/processed/finance_material"
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out/"observations.csv", index=False)

    def pick(entity, variable, valid=None, **filters):
        selected = [r for r in claims if r["entity_id"] == entity and r["variable"] == variable
                    and (valid is None or r["valid_date"] == valid)
                    and all(r.get(k) == v for k,v in filters.items())]
        if len(selected) != 1:
            raise ValueError(f"Ambiguous accounting/product selection: {entity} {variable}")
        return selected[0]

    cash = []
    for year in [2024, 2025]:
        values = [pick("Pensana_consolidated", v, f"{year}-12-31")["value"] for v in
                  ["ppe_additions", "saltend_intangible_additions", "total_additions", "capital_working_capital_adjustment", "cash_ppe_intangibles_payments"]]
        cash.append(dict(period_start=f"{year}-07-01", period_end=f"{year}-12-31", currency="USD", **cash_reconciliation(*values)))
    facility = []
    limit = pick("Iluka_EFA_facility", "base_limit")["value"]
    for date in ["2025-12-31", "2026-06-30"]:
        drawn, undrawn = [pick("Iluka_EFA_facility", v, date)["value"] for v in ["drawn", "undrawn"]]
        facility.append(dict(date=date, currency="AUD million", limit_basis="reported base limit; prior balance identity does not establish unrestricted draw eligibility", **facility_reconciliation(limit, drawn, undrawn)))
    if not all(r["passed"] for r in cash+facility):
        raise ValueError("Reported financial identity failed; context/revision review required")
    ratios = []
    for product in ["NdPr_oxide_family", "DyTb_oxide_combined"]:
        a = pick("Iluka_Eneabba", "prospective_product_quantity", feed_case="stockpile_only", product_basis=product)
        b = pick("Iluka_Eneabba", "prospective_product_quantity", feed_case="additional_feedstocks", product_basis=product)
        result = planned_capacity_retention(a["value"], b["value"], product_base=a["product_basis"], product_expanded=b["product_basis"], unit_base=a["native_unit"], unit_expanded=b["native_unit"])
        ratios.append(dict(product_basis=product, stockpile_only_native=a["value"], expanded_native=b["value"], native_unit=a["native_unit"], **result))
    pd.DataFrame(ratios).to_csv(out/"prospective_product_comparisons.csv", index=False)
    comparison_out = ROOT/"outputs/empirical/rare_earths"
    fig, ax = plt.subplots(figsize=(7, 3.5))
    bars = ax.barh(["NdPr oxide family", "Combined Dy/Tb oxide family"], [r["stockpile_only_to_expanded_ratio"] for r in ratios], color=["#236a8a", "#8a669e"])
    for bar, r in zip(bars, ratios):
        ax.text(bar.get_width()+.02, bar.get_y()+bar.get_height()/2, f"{100*r['stockpile_only_to_expanded_ratio']:.1f}%", va="center", fontsize=9)
    ax.set(xlim=(0,1), xlabel="Ratio of same-product prospective native figures", title="Eneabba: stockpile-only / additional-feedstock comparison")
    fig.text(.5, -.04, "Issuer plans, not observed output or China-free magnet service. Annual time basis,\nDy/Tb split, feed contracts, recoveries, routing and final demand remain unresolved.", ha="center", fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:
        fig.savefig(comparison_out/f"eneabba_feedstock_comparison.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    left = axes[0]
    values = [-pick("Pensana_consolidated", v, "2025-12-31")["value"]/1e6 for v in ["ppe_additions", "saltend_intangible_additions", "capital_working_capital_adjustment"]]
    left.bar(["PPE\nadditions", "Saltend\nintangibles", "Capital working\ncapital"], values, color=["#236a8a", "#8a669e", "#ba8a4c"])
    left.set(title="Pensana: Jul–Dec 2025 reconciliation", ylabel="USD millions (magnitudes)", ylim=(0,13))
    left.text(.5, .96, "Sum = USD 15.999m cash payments", transform=left.transAxes, ha="center", va="top", fontsize=9)
    right = axes[1]
    drawn, undrawn = [pick("Iluka_EFA_facility", v, "2026-06-30")["value"] for v in ["drawn", "undrawn"]]
    right.barh(["EFA base facility"], [drawn], label="Reported drawn", color="#236a8a")
    right.barh(["EFA base facility"], [undrawn], left=[drawn], label="Undrawn; conditions apply", color="#b9c5cf")
    right.set(title="Iluka: 30 Jun 2026 credit balances", xlabel="AUD millions; base limit 1,650", xlim=(0,1750))
    right.legend(loc="lower center", bbox_to_anchor=(.5,-.48), fontsize=8)
    fig.text(.5, -.1, "Different currencies and accounting objects; never aggregated. Additional AUD75m overrun allowance is separate.\nDebt, commitments and proposed investments are not cash spent, physical output or causal effects.", ha="center", fontsize=8)
    fig.tight_layout()
    for ext in ["pdf","png"]:
        fig.savefig(comparison_out/f"project_finance_categories.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    report = dict(passed=True, claims=len(claims), original_reports=len(pages),
                  cash_reconciliations=cash, facility_reconciliations=facility,
                  prospective_product_comparisons=ratios, physical_network_service_identified=False,
                  causal_financing_response_identified=False, independent_historical_byte_vintage_certified=False,
                  statement="Actual issuer disclosures and derived accounting identities; plans, balances, obligations, reserves and flows remain distinct")
    (ROOT/"outputs/diagnostics/finance_material_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != "prospective_product_comparisons"}, indent=2))


if __name__ == "__main__":
    build()
