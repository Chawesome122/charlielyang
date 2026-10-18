#!/usr/bin/env python3
"""Restore a locally needed, nonredistributed original from its public publisher.

Existing bytes must match the recorded digest. New mismatching bytes are retained
in quarantine and never substituted for the pre-freeze reference version.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--fetch", action="store_true", help="Download missing source; never replace a different source vintage")
    args = parser.parse_args()
    sources = pd.read_csv(ROOT/"metadata/literature_sources.csv").fillna("")
    row = sources[sources.artifact_id.eq("R02_pdf")].iloc[0]
    target = ROOT/row.path
    report = dict(source_id="R02_pdf", path=row.path, expected_sha256=row.sha256,
                  publisher_url=row.url, redistribution="full NBER paper and extracted full text omitted from Git")
    if target.exists():
        report.update(present=True, actual_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        report["passed"] = report["actual_sha256"] == row.sha256
        report["action"] = "existing local original checked; no download performed"
    elif not args.fetch:
        report.update(passed=False, present=False, action="Run with --fetch or lawfully supply exact original bytes")
    else:
        try:
            with urlopen(Request(row.url, headers={"User-Agent":"AcademicResearchReplication/1.0"}), timeout=40) as response:
                data = response.read()
            digest = hashlib.sha256(data).hexdigest()
            report.update(actual_sha256=digest, present=True, passed=(digest == row.sha256))
            destination = target if report["passed"] else ROOT/"data/quarantine"/(digest + ".bin")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            report["saved_path"] = str(destination.relative_to(ROOT))
            report["action"] = "exact original restored" if report["passed"] else "different revision/response quarantined; original remains unavailable"
        except (URLError, HTTPError, TimeoutError) as error:
            report.update(passed=False, present=False, action="publisher acquisition failed", error=str(error))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
