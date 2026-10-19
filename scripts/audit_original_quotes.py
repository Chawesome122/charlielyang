"""Recheck legacy quotations and quarterly KPI cells against original bytes."""
import json
from pathlib import Path

import pandas as pd

from weaponized.io.original_text import evidence_pdf_page, verified_original_text, verify_original_quote
from weaponized.rare_earths.reported_output import parse_lynas_quarterly_front_page

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for row in pd.read_csv(ROOT/"metadata/additional_rare_earth_sources.csv").fillna("").to_dict("records"):
        sources[row["source_id"]] = row
    tables = [
        "data/processed/rare_earths/observations.csv",
        "data/processed/rare_earths/project_state_evidence.csv",
        "data/processed/rare_earths_additional/lynas_project_history.csv",
        "data/processed/industrial_evidence/project_milestones.csv",
        "data/processed/industrial_evidence/technical_claims.csv",
        "data/processed/project_histories/milestone_versions.csv",
        "data/processed/finance_material/observations.csv",
        "data/processed/engineering_inputs/observations.csv",
        "data/processed/white_mesa/observations.csv",
    ]
    checks = []
    for table in tables:
        for number, row in enumerate(pd.read_csv(ROOT/table).fillna("").to_dict("records")):
            source = sources[row["source_id"]]
            page = evidence_pdf_page(row)
            quote = row["quote"]
            passed = row["source_sha256"] == source["sha256"] and verify_original_quote(
                ROOT/source["archive_path"], source["sha256"], quote, page)
            checks.append(dict(table=table, row_index=number, source_id=row["source_id"],
                               source_sha256=source["sha256"], pdf_page=page,
                               method="normalized verbatim quote in hash-verified original",
                               passed=passed))
    table = "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv"
    parsed = {}
    for number, row in enumerate(pd.read_csv(ROOT/table).to_dict("records")):
        source = sources[row["source_id"]]
        if row["source_id"] not in parsed:
            text = verified_original_text(ROOT/source["archive_path"], source["sha256"])
            parsed[row["source_id"]] = parse_lynas_quarterly_front_page(text.split("\f")[0])
        keys = ["period_end", "fiscal_quarter", "product_basis", "value", "source_unit_token", "comparative", "report_period_end"]
        matches = [item for item in parsed[row["source_id"]] if all(item[key] == row[key] for key in keys)]
        checks.append(dict(table=table, row_index=number, source_id=row["source_id"],
                           source_sha256=source["sha256"], pdf_page=1,
                           method="reparse original three-column quarterly KPI header and cells",
                           passed=len(matches) == 1 and row["source_sha256"] == source["sha256"]))
    out = ROOT/"data/processed/source_integrity"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(out/"original_quote_audit.csv", index=False)
    result = dict(passed=all(row["passed"] for row in checks), checks=len(checks),
                  tables=len(tables)+1, original_sources=len({row["source_id"] for row in checks}),
                  failures=[row for row in checks if not row["passed"]],
                  editable_text_aids_used=False, independent_production_measurement=False,
                  historical_source_byte_vintage_certified=False,
                  scope="Present archived original-byte support, not historical release certification or independent economic truth")
    (ROOT/"outputs/diagnostics/original_quote_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
