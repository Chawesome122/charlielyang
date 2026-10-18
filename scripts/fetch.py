#!/usr/bin/env python3
"""Replay a public-source registry; offline reproduction never needs this step."""
import argparse
import json
from pathlib import Path
from weaponized.io.archive import fetch_source, append_record


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--registry", default="metadata/source_registry.json")
    p.add_argument("--group", default="rare_earths")
    p.add_argument("--retry-failures", action="store_true")
    args = p.parse_args()
    records = json.loads(Path(args.registry).read_text())
    failed = 0
    for record in records:
        if record.get("group") != args.group:
            continue
        path = record.get("archive_path")
        if path and Path(path).is_file():
            continue
        if record.get("status") == "failed" and not args.retry_failures:
            continue
        result = fetch_source(record["url"], record["source_id"], f"data/raw/{args.group}",
                              record.get("publication_date"))
        append_record(result, "metadata/reacquisition_attempts.jsonl")
        failed += result["status"] == "failed"
        print(record["source_id"], result["status"])
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
