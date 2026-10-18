"""Archive bibliographic evidence without treating metadata as claim verification.

Network acquisition is an explicit optional step; analysis uses saved artifacts.
Crossref is the DOI registration authority, not a substitute for reading originals.
"""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOIS = {
    "R01": "10.1162/isec_a_00351", "R02": "10.3386/w33309",
    "R03": "10.1007/s44216-026-00073-z", "R04": "10.1007/s10666-022-09819-4",
    "R05": "10.1111/twec.13570", "R06": "10.1057/s41599-024-03369-8",
    "R07": "10.1111/ecpo.70033", "R08": "10.3982/ECTA6248",
    "R09": "10.1093/rfs/hhv050", "R10": "10.1257/pol.20140068",
    "R11": "10.1515/9781400830176", "R11_jstor": "10.2307/j.ctt7sncv",
    "R12": "10.1111/j.2517-6161.1972.tb00899.x",
    "R13": "10.1080/01621459.1999.10474144", "R14": "10.1016/j.jeconom.2020.12.001",
    "R15": "10.1016/j.jeconom.2020.09.006", "R16": "10.3386/w32117",
    "R17": "10.1198/016214506000001437", "R19": "10.1006/jeth.2000.2785",
    "R18": "10.1175/1520-0493(1950)078<0001:vofeit>2.0.co;2", "R20": "10.32917/hmj/1206139508",
    "R21": "10.1111/1468-0262.00241", "R22": "10.1007/978-0-8176-4755-1",
    "R23": "10.1086/226707", "R24": "10.1073/pnas.082090499",
    "R36": "10.1093/ej/ueag111", "R37": "10.1080/0022250X.1971.9989794",
    "R38": "10.2307/2234208",
}
ORIGINALS = {
    "R01_publisher": "https://direct.mit.edu/isec/article/44/1/42/12237/Weaponized-Interdependence-How-Global-Economic",
    "R02_nber": "https://www.nber.org/papers/w33309",
    "R02_pdf": "https://www.nber.org/system/files/working_papers/w33309/w33309.pdf",
    "R03_publisher": "https://link.springer.com/article/10.1007/s44216-026-00073-z",
    "R04_publisher": "https://link.springer.com/article/10.1007/s10666-022-09819-4",
    "R05_publisher": "https://onlinelibrary.wiley.com/doi/10.1111/twec.13570",
    "R06_publisher": "https://www.nature.com/articles/s41599-024-03369-8",
    "R06_pdf": "https://www.nature.com/articles/s41599-024-03369-8.pdf",
    "R07_publisher": "https://onlinelibrary.wiley.com/doi/10.1111/ecpo.70033",
    "R36_publisher": "https://academic.oup.com/ej/advance-article/doi/10.1093/ej/ueag111/",
}


def download(item: tuple[str, str]) -> dict:
    key, url = item
    directory = ROOT / "data/raw/literature"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    row = {"artifact_id": key, "url": url, "retrieval_timestamp": stamp,
           "http_status": "", "path": "", "sha256": "", "bytes": 0, "error": ""}
    request = urllib.request.Request(url, headers={"User-Agent": "AcademicResearchReplication/1.0 (public bibliographic verification)", "Accept": "application/json,text/html,application/pdf;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = response.read()
            row["http_status"] = response.status
            row["resolved_url"] = response.url
            content_type = response.headers.get("Content-Type", "")
        extension = ".json" if "json" in content_type else ".pdf" if data.startswith(b"%PDF") else ".html"
        path = directory / (key + extension)
        # A rerun never silently replaces an earlier source version.
        if path.exists() and path.read_bytes() != data:
            path = directory / (key + "_" + hashlib.sha256(data).hexdigest()[:12] + extension)
        path.write_bytes(data)
        row.update(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    except Exception as exc:
        row["error"] = str(exc)
        row["http_status"] = getattr(exc, "code", "")
    return row


def main() -> None:
    jobs = [(key + "_crossref", "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")) for key, doi in DOIS.items()]
    jobs.extend(ORIGINALS.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(executor.map(download, jobs))
    directory = ROOT / "metadata"
    directory.mkdir(exist_ok=True)
    path = directory / "literature_sources.csv"
    fields = ["artifact_id", "url", "resolved_url", "retrieval_timestamp", "http_status", "path", "sha256", "bytes", "error"]
    if path.exists():
        old_digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        (directory / ("literature_sources_previous_" + old_digest + ".csv")).write_bytes(path.read_bytes())
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row["artifact_id"], row["http_status"], row["bytes"], row["error"])


if __name__ == "__main__":
    main()
