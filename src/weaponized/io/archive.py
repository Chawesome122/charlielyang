"""Content-addressed source acquisition with explicit failure records.

Retrieval time never substitutes for first public availability. HTTP success alone
does not establish an artifact's historical eligibility or a claim's correctness.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_bytes(data: bytes, directory: str | Path, suffix: str = ".bin") -> Path:
    """Never replace a different version; each digest has its own immutable path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    path = directory / (digest + suffix)
    if path.exists():
        if sha256_file(path) != digest:
            raise ValueError(f"Corrupted archive: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(data)
    return path


def fetch_source(url: str, source_id: str, directory: str | Path,
                 publication_date: str | None = None, timeout: int = 40) -> dict:
    """Fetch one public resource; return provenance or the exact failed operation."""
    record = dict(source_id=source_id, url=url, publication_date=publication_date,
                  retrieval_timestamp=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": "WeaponizedInterdependenceResearch/0.1 (public source archival)"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            mime = response.headers.get("Content-Type", "application/octet-stream")
            if not data:
                raise ValueError("Empty response")
            suffix = ".pdf" if data.startswith(b"%PDF") else ".json" if "json" in mime else ".html"
            path = archive_bytes(data, directory, suffix)
            record.update(status="downloaded", http_status=response.status,
                          content_type=mime, sha256=sha256_file(path), bytes=len(data),
                          archive_path=str(path), final_url=response.url,
                          redistribution="access terms unreviewed; retain local research copy")
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
    return record


def append_record(record: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
