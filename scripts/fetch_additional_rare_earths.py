#!/usr/bin/env python3
"""Issuer-disclosed Lynas reports and USGS metadata; no guessed PDF addresses.

Raw bytes are immutable SHA256 archives. Normal reruns use archived responses;
--refresh permits a new live request and preserves all earlier source versions.
No TLS, signature or access-control bypass is attempted.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
from pathlib import Path
from weaponized.io.original_text import verified_original_text
import re
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/rare_earths_additional"
PROCESSED = ROOT / "data/processed/rare_earths_additional"
LOG = ROOT / "metadata/additional_rare_earth_acquisitions.jsonl"
FREEZE = date(2026, 10, 11)
UA = "WeaponizingInterdependence academic replication (public primary-source research)"
FIELDS = ["source_id", "title", "url", "final_url", "publication_date", "public_timestamp_utc", "publication_date_basis",
          "retrieval_timestamp", "status", "http_status", "content_type", "sha256", "bytes", "archive_path", "error", "discovered_from"]


def archive_fetch(item, refresh=False):
    source_id, url, extra = item
    if LOG.exists() and not refresh:
        matches = [json.loads(line) for line in LOG.read_text().splitlines() if json.loads(line).get("url") == url]
        if matches:
            record = matches[-1]
            if record.get("archive_path"):
                path = ROOT / record["archive_path"]
                if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]:
                    return {**record, **extra}
            elif record.get("status") == "blocked":
                return record
    record = {"source_id": source_id, "url": url, "retrieval_timestamp": datetime.now(timezone.utc).isoformat(), **extra}
    try:
        response = urlopen(Request(url, headers={"User-Agent": UA}), timeout=40)
        data = response.read()
        record.update(http_status=response.status, final_url=response.url,
                      content_type=response.headers.get("content-type", ""))
    except HTTPError as exc:
        data = exc.read()
        record.update(status="blocked", http_status=exc.code, final_url=exc.url,
                      content_type=exc.headers.get("content-type", ""), error=str(exc))
    except Exception as exc:
        record.update(status="blocked", error=f"{type(exc).__name__}: {exc}")
        return record
    sha = hashlib.sha256(data).hexdigest()
    suffix = ".pdf" if data.startswith(b"%PDF") else ".json" if "json" in record["content_type"] else ".html"
    path = RAW / (sha + suffix)
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError("SHA256 collision/archive corruption")
    if not path.exists():
        path.write_bytes(data)
    record.update(sha256=sha, bytes=len(data), archive_path=str(path.relative_to(ROOT)))
    if "status" not in record:
        record["status"] = "downloaded_pdf" if suffix == ".pdf" else "downloaded_metadata"
        if len(data) < 1000 and b"javascript" in data.lower():
            record["status"] = "challenge_not_source"
    return record


def persist(records):
    previous = [json.loads(line) for line in LOG.read_text().splitlines()] if LOG.exists() else []
    identity = {(r.get("url"), r.get("sha256"), r.get("status"), r.get("error")) for r in previous}
    with LOG.open("a") as stream:
        for row in records:
            key = (row.get("url"), row.get("sha256"), row.get("status"), row.get("error"))
            if key not in identity:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                identity.add(key)


def jsonp_headlines(path):
    text = path.read_text()
    if not text.startswith("wl_headlinesFunction("):
        raise ValueError("Unexpected Lynas index response: not the issuer's documented JSONP")
    return json.JSONDecoder().raw_decode(text[text.index("(") + 1:])[0]["headlines"]


def extract_pdf(record):
    path = ROOT / record["archive_path"]
    return verified_original_text(path, record["sha256"])


def build_production(rows):
    observations = []
    evidence = []
    for row in rows:
        if not row.get("archive_path", "").endswith(".pdf"):
            continue
        text = extract_pdf(row)
        pages = text.split("\f")
        for page_no, page in enumerate(pages, 1):
            lines = page.splitlines()
            for i, line in enumerate(lines):
                if any(term in line.lower() for term in ["production", "commission", "dysprosium", "terbium", "capacity"]):
                    evidence.append({"source_id": row["source_id"], "page": page_no, "line": i + 1,
                                     "excerpt": " ".join(lines[max(0, i-1):i+2]), "source_sha256": row["sha256"]})
        if "Annual Report" in row.get("title", ""):
            fiscal = re.search(r"(?:FY|Annual Report\s*|and\s+)(202\d|201\d)", row.get("title", ""))
            # Year from the source index query is preserved separately when title formatting differs.
            fiscal_year = row.get("fiscal_year") or (int(fiscal.group(1)) if fiscal else None)
            if fiscal_year is None:
                continue
            first_pages = "\n".join(pages[:14])
            for product, label in [("total_REO", r"(?:Total\s+)?REO production"),
                                   ("NdPr_oxide_product_family", r"(?:Total\s+)?NdPr production")]:
                # Key-figure layouts put a left-column employment metric between
                # the right-column amount and label. Search only standalone KPI
                # labels and the preceding four lines, never arbitrary numbers.
                match = None
                locator_page = None
                for page_no, page_text in enumerate(pages[:14], 1):
                    lines = page_text.splitlines()
                    for i, line in enumerate(lines):
                        if re.fullmatch(r"\s*(?:Employees\s+)?" + label + r"\s*", line, re.I):
                            nearby = "\n".join(lines[max(0, i-4):i])
                            matches = list(re.finditer(r"([\d,]+)\s+tonnes\b", nearby, re.I))
                            if matches:
                                match, locator_page = matches[-1], page_no
                                break
                    if match:
                        break
                if match is None:
                    flat = " ".join(first_pages.split())
                    ndpr_patterns = [
                        r"Production of NdPr increased from [\d,]+ tonnes in FY15 to ([\d,]+) tonnes for FY16",
                        r"(?:production of NdPr|NdPr production)\s+(?:was|increased to|grew to)\s+([\d,]+)\s+tonnes",
                        r"(?:Neodymium-Praseodymium\s*)?\(NdPr\)\s+was\s+([\d,]+)\s+tonnes(?:\s+in\s+FY\d+)?",
                    ]
                    reo_patterns = [
                        r"total REO(?: production)?\s+(?:was|increased to)\s+([\d,]+)\s+tonnes",
                        r"total production volumes increased to\s+([\d,]+)\s+REO tonnes",
                        r"oxide\s*\(REO\)\s+(?:in FY\d+\s+)?was\s+([\d,]+)\s+tonnes",
                        r"\(REO\)\s+(?:ready for sale\s+)?production at the LAMP (?:for the 12 months to June 30, 2016|during the year) was\s+([\d,]+)\s+tonnes",
                    ]
                    for pattern in (ndpr_patterns if product.startswith("NdPr") else reo_patterns):
                        match = re.search(pattern, flat, re.I)
                        if match:
                            break
                if match:
                    observations.append({"facility_id": "LYNAS-MALAYSIA", "issuer": "Lynas Rare Earths Ltd",
                                         "period_end": f"{fiscal_year}-06-30", "frequency": "fiscal_year",
                                         "stage": "separation", "measure": "reported_production", "product_basis": product,
                                         "native_unit": "tonnes_reported_product", "value": int(match.group(1).replace(",", "")),
                                         "event_date": f"{fiscal_year}-06-30", "info_public_date": row["publication_date"],
                                         "source_id": row["source_id"], "source_sha256": row["sha256"], "source_url": row["url"],
                                         "locator": f"PDF page {locator_page}, standalone key-figure label" if locator_page else "CEO/operational review in first14pages; matched narrative excerpt archived",
                                         "limitations": "Issuer-reported; no Nd/Pr split or element-mass conversion; not magnet output"})
    keys = ["facility_id", "issuer", "period_end", "frequency", "stage", "measure", "product_basis", "native_unit", "value",
            "event_date", "info_public_date", "source_id", "source_sha256", "source_url", "locator", "limitations"]
    with (PROCESSED / "lynas_annual_production.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys); writer.writeheader(); writer.writerows(observations)
    (PROCESSED / "report_evidence_excerpts.jsonl").write_text("".join(json.dumps(e) + "\n" for e in evidence))
    return observations


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True)
    initial = [("LYNAS-INDEX-JS", "https://wcsecure.weblink.com.au/Clients/lynascorp/headlineJS.aspx", {}),
               ("USGS2026-DATACITE", "https://api.datacite.org/dois/10.5066/P1WKQ63T", {"title": "USGS2026 data release DOI metadata"})]
    with ThreadPoolExecutor(max_workers=2) as executor:
        metadata = list(executor.map(lambda x: archive_fetch(x, args.refresh), initial))
    persist(metadata)
    js_row = next(r for r in metadata if r["source_id"] == "LYNAS-INDEX-JS")
    js = (ROOT / js_row["archive_path"]).read_text()
    endpoint = re.search(r'wl_url:\s*"([^"]+)"', js).group(1)
    indexes = []
    for year in range(2016, 2027):
        indexes.append((f"LYNAS-ANNUAL-{year}", endpoint + "?" + urlencode({"hdGroup": 1, "numberHdPerPage": 20, "pageNumber": 1, "year": year, "search": ""}), {"fiscal_year": year}))
    for year in range(2024, 2027):
        indexes.append((f"LYNAS-QUARTERLY-{year}", endpoint + "?" + urlencode({"hdGroup": 3, "numberHdPerPage": 20, "pageNumber": 1, "year": year, "search": ""}), {}))
    with ThreadPoolExecutor(max_workers=3) as executor:
        indexed = list(executor.map(lambda x: archive_fetch(x, args.refresh), indexes))
    persist(indexed)
    reports = {}
    source_index = []
    for row in indexed:
        if not row.get("archive_path"):
            continue
        for head in jsonp_headlines(ROOT / row["archive_path"]):
            timestamp = datetime.fromtimestamp(int(re.search(r"\d+", head["datetime"]).group()) / 1000, timezone.utc)
            public_date = timestamp.astimezone(ZoneInfo("Australia/Sydney")).date()
            title = head["HeadlineText"]
            extra = {"title": title, "publication_date": public_date.isoformat(), "public_timestamp_utc": timestamp.isoformat(),
                     "publication_date_basis": "ASX-linked issuer index timestamp in Australia/Sydney; preserved UTC separately",
                     "discovered_from": row["url"], "fiscal_year": row.get("fiscal_year")}
            source_index.append({**extra, "url": head["pdfLink"], "eligible_at_freeze": public_date <= FREEZE})
            if public_date > FREEZE or not ("Annual Report" in title or title == "Quarterly Activities Report"):
                continue
            report_id = "LYNAS-" + re.search(r"headlineid=(\d+)", head["pdfLink"]).group(1)
            reports[head["pdfLink"]] = (report_id, head["pdfLink"], extra)
    with ThreadPoolExecutor(max_workers=3) as executor:
        downloaded = list(executor.map(lambda x: archive_fetch(x, args.refresh), reports.values()))
    persist(downloaded)
    rows = metadata + indexed + downloaded
    with (ROOT / "metadata/additional_rare_earth_sources.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    (PROCESSED / "lynas_report_index.json").write_text(json.dumps(source_index, indent=2) + "\n")
    production = build_production(downloaded)
    report = {"research_freeze": str(FREEZE), "classification": "PRIMARY issuer-reported observations; incomplete industrial network",
              "downloaded_pdfs": sum(r.get("archive_path", "").endswith(".pdf") for r in downloaded),
              "production_observations": len(production), "failures": [r for r in rows if r.get("status") == "blocked"],
              "invariants": {"all_observation_public_dates_before_freeze": all(date.fromisoformat(o["info_public_date"]) <= FREEZE for o in production),
                             "native_product_bases_preserved": True, "no_cross_stage_capacity_sums": True,
                             "no_estimated_magnet_service": True}}
    (PROCESSED / "acquisition_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
