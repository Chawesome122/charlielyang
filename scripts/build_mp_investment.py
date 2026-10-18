"""Extract actual SEC cash-flow inputs, keeping duration and source vintages."""
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/weaponized-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from weaponized.io.archive import sha256_file
from weaponized.io.vintages import select_asof
from weaponized.rare_earths.investment import extract_cash_ppe_versions

ROOT = Path(__file__).resolve().parents[1]


def main():
    index = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    source = index["RE-MP-FACTS"]
    if sha256_file(ROOT/source["archive_path"]) != source["sha256"]:
        raise ValueError("SEC companyfacts archive hash mismatch")
    versions = extract_cash_ppe_versions(json.loads((ROOT/source["archive_path"]).read_text()), "RE-MP-FACTS", source["sha256"])
    latest = select_asof(versions, "2026-10-11")
    output = ROOT/"data/processed/industrial_evidence"
    versions.to_csv(output/"mp_cash_ppe_versions.csv", index=False)
    latest.to_csv(output/"mp_cash_ppe_asof_freeze.csv", index=False)
    half = latest[latest.period_start.str.endswith("01-01") & latest.period_end.str.endswith("06-30")].copy()
    half["year"] = half.period_end.str[:4].astype(int)
    half = half.sort_values("year")
    half.to_csv(ROOT/"outputs/empirical/rare_earths/mp_halfyear_cash_ppe.csv", index=False)
    checks = []
    for row in half.itertuples():
        q1 = latest[latest.period_start.eq(f"{row.year}-01-01") & latest.period_end.eq(f"{row.year}-03-31")]
        q2 = latest[latest.period_start.eq(f"{row.year}-04-01") & latest.period_end.eq(f"{row.year}-06-30")]
        if len(q1) == 1 and len(q2) == 1:
            delta = float(q1.iloc[0].value + q2.iloc[0].value-row.value)
            checks.append(dict(year=int(row.year), q1_plus_q2_minus_h1_usd=delta, passed=abs(delta) <= 1))
    if not all(row["passed"] for row in checks):
        raise ValueError("Reported quarter/H1 mismatch requires context/revision adjudication")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(half.year.astype(str), half.value/1e6, color="#236a8a")
    ax.set(title="MP Materials: reported first-half cash payments for PPE", xlabel="Calendar year; January–June duration", ylabel="USD millions, nominal")
    fig.text(.5, -.035, "SEC companyfacts, latest source vintages by 2026-10-11.\nConsolidated cash inputs; no project allocation, physical-output or causal-effect inference.", ha="center", fontsize=8)
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(ROOT/f"outputs/empirical/rare_earths/mp_halfyear_cash_ppe.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    report = dict(passed=True, versioned_records=len(versions), distinct_reported_durations=len(latest),
                  halfyear_values_usd={str(row.year):float(row.value) for row in half.itertuples()},
                  quarter_halfyear_reconciliations=checks,
                  input_class="actual reported nominal cash-flow input, not project spending allocation or output",
                  causal_response_identified=False, forecast_skill_established=False,
                  limitation="official archived companyfacts representation; original quarterly filing/XBRL context reconciliation remains blocked")
    (ROOT/"outputs/diagnostics/mp_investment_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
