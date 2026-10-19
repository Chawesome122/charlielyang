"""Resolve archived exact-link public clocks while retaining unresolved reports."""
import json
from pathlib import Path

import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.io.publication import linked_publication_clock

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/"data/processed/rare_earths/source_index.json"
    sources = json.loads(path.read_text())
    specs = [
        ("RE-PENSANA-CONSTRUCTION-PDF", "RE-PENSANA-CONSTRUCTION", "article_jsonld"),
        ("RE-PENSANA-INTERIM-PDF", "RE-PENSANA-INTERIM2025", "article_jsonld"),
        ("RE-ILUKA-HALF2026", "RE-ILUKA", "dated_link_card"),
        ("RE-ILUKA-OFFTAKE2026", "RE-ILUKA", "dated_link_card"),
        ("RE-ILUKA-ANNUAL2025", "RE-ILUKA", "dated_link_card"),
        ("RE-PENSANA-ANNUAL2023", "RE-PENSANA-REPORTS", "dated_link_card"),
        ("RE-PENSANA-ANNUAL2024", "RE-PENSANA-REPORTS", "dated_link_card"),
        ("RE-PENSANA-ANNUAL2025", "RE-PENSANA-REPORTS", "dated_link_card"),
    ]
    records = []
    for sid, clock_id, method in specs:
        source, clock = sources[sid], sources[clock_id]
        for row in [source, clock]:
            if sha256_file(ROOT/row["archive_path"]) != row["sha256"]:
                raise ValueError("Report or publication-evidence archive checksum mismatch")
        record = dict(source_id=sid, source_sha256=source["sha256"], report_url=source["url"],
                      public_clock_source_id=clock_id, public_clock_source_sha256=clock["sha256"],
                      public_clock_url=clock["url"], method=method)
        try:
            result = linked_publication_clock((ROOT/clock["archive_path"]).read_text(), clock["url"], source["url"], method)
            record.update(result, status="RESOLVED")
            # The raw acquisition record remains immutable. Only this derived
            # source index receives an explicitly traceable clock resolution.
            source.update(publication_date=result["info_public_date"],
                          publication_basis=result["basis"], public_clock_source_id=clock_id,
                          public_clock_source_sha256=clock["sha256"])
        except ValueError as error:
            record.update(status="UNRESOLVED", info_public_date=None, reason=str(error))
        records.append(record)
    out = ROOT/"data/processed/finance_material"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(out/"publication_clock_audit.csv", index=False)
    path.write_text(json.dumps(sources, indent=2))
    result = dict(passed=True, resolved=sum(r["status"] == "RESOLVED" for r in records),
                  unresolved=sum(r["status"] == "UNRESOLVED" for r in records),
                  unresolved_dates_are_not_estimates=True, raw_acquisition_records_modified=False)
    (ROOT/"outputs/diagnostics/publication_clock_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
