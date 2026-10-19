"""Extract claim evidence from hash-verified originals, never editable text aids.

This checks present archived bytes, not their original publication vintage or
the economic truth of a statement. Extraction uses one immutable byte snapshot;
the digest is checked on every access and the cache is keyed by bytes/form.
"""
from functools import lru_cache
import hashlib
from pathlib import Path
import re
import subprocess

from bs4 import BeautifulSoup

def normalize_evidence(text: str) -> str:
    return " ".join(text.replace("\u200b", "").split())


@lru_cache(maxsize=128)
def _extract(payload: bytes, suffix: str) -> str:
    if suffix == ".pdf":
        return subprocess.check_output(["pdftotext", "-layout", "-", "-"], input=payload).decode("utf-8")
    if suffix not in {".html", ".htm", ".xhtml"}:
        raise ValueError("Original evidence extraction supports PDF and HTML only")
    soup = BeautifulSoup(payload.decode("utf-8"), "html.parser")
    for element in soup.select("script,style,ix\\:header"):
        element.decompose()
    return soup.get_text(" ", strip=True)


def verified_original_text(path: str | Path, digest: str) -> str:
    source = Path(path).resolve()
    payload = source.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Original source checksum mismatch: {source.name}")
    return _extract(payload, source.suffix.lower())


def evidence_pdf_page(row: dict) -> int | None:
    """Respect an explicit page column and/or anchored page locator."""
    raw = row.get("pdf_page")
    explicit = None
    if raw is not None and raw != "":
        numeric = float(raw)
        if isinstance(raw, bool) or not numeric.is_integer() or numeric < 1:
            raise ValueError("Invalid explicit PDF page")
        explicit = int(numeric)
    locator = str(row.get("locator", ""))
    match = re.match(r"^PDF page ([1-9][0-9]*)(?=$|[;,]|\s)", locator)
    if locator.startswith("PDF page ") and not match:
        raise ValueError("Invalid PDF page locator")
    located = int(match[1]) if match else None
    if explicit is not None and located is not None and explicit != located:
        raise ValueError("PDF page column conflicts with extraction locator")
    return explicit if explicit is not None else located


def verify_original_quote(path: str | Path, digest: str, quote: str, page: int | None = None) -> bool:
    normalized = normalize_evidence(quote)
    if not normalized:
        raise ValueError("An empty quote cannot verify a claim")
    text = verified_original_text(path, digest)
    if page is not None:
        if Path(path).suffix.lower() != ".pdf" or not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError("A positive integer PDF page is required")
        pages = text.split("\f")
        if page > len(pages) or not pages[page-1].strip():
            raise ValueError("PDF evidence page is absent or empty")
        text = pages[page-1]
    return normalized in normalize_evidence(text)
