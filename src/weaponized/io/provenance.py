"""Manifest and source-to-claim integrity checks."""
import hashlib
import json
from pathlib import Path
from .archive import sha256_file


def verify_sources(records: list[dict], root: str | Path = ".") -> dict:
    failures, checked = [], 0
    root = Path(root)
    for record in records:
        if record.get("status") != "downloaded":
            continue
        path = root / record["archive_path"]
        checked += 1
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            failures.append(record["source_id"])
    return {"checked": checked, "failures": failures, "passed": not failures}


def canonical_digest(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()
