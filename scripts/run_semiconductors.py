#!/usr/bin/env python3
"""Acquire original legal documents and rebuild semiconductor evidence outputs.

Source acquisition is opt-in (--fetch); normal replication uses archived bytes.
All fetch outcomes, including HTTP errors, are retained in a separate manifest.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))
sys.path.insert(0, str(ROOT / "src"))
from weaponized.semiconductors.evidence import EVIDENCE_COLUMNS, estimate_semiconductor_states
from weaponized.semiconductors.events import forecast_availability, identification_feasibility
from weaponized.semiconductors.legal import LEGAL_COLUMNS, validate_legal_events
from weaponized.io.original_text import verified_original_text

FREEZE = "2026-10-11"
RAW = ROOT / "data/raw/semiconductors"
PROCESSED = ROOT / "data/processed/semiconductors"
OUTPUT = ROOT / "outputs/empirical/semiconductors"
MANIFEST = ROOT / "metadata/semiconductor_sources.csv"
DOCUMENTS = [
    "2022-17125", "2022-21658", "2022-26662", "2023-00888",
    "2023-22873", "2023-23049", "2023-23055", "2023-23312",
    "2024-07004", "2024-19633", "2024-22587", "2024-28267",
    "2024-28270", "2025-00636", "2025-00711", "2025-16735", "2026-00789",
]
OTHER_SOURCES = [
    ("SC-NL-2023-06-30", "https://www.government.nl/latest/news/2023/06/30/additional-export-control-measures-for-advanced-semiconductor-manufacturing-equipment", "2023-06-30", "html"),
    ("SC-NL-2024-09-06", "https://www.government.nl/latest/news/2024/09/06/the-netherlands-expands-export-control-measure-for-advanced-semiconductor-manufacturing-equipment", "2024-09-06", "html"),
    ("SC-NL-2025-01-15", "https://www.government.nl/latest/news/2025/01/15/klever-export-controls-on-advanced-semiconductor-manufacturing-equipment-to-be-tightened", "2025-01-15", "html"),
    ("SC-NL-ORDER-2025-1894", "https://www.officielebekendmakingen.nl/stcrt-2025-1894.html", "2025-01-15", "html"),
    ("SC-NL-ORDER-2023-18212", "https://www.officielebekendmakingen.nl/stcrt-2023-18212.html", "2023-06-30", "html"),
    ("SC-JP-LAW-INDEX", "https://www.meti.go.jp/policy/anpo/law09-2.html", None, "html"),
    ("SC-JP-2023-05-23-CANDIDATE", "https://www.meti.go.jp/english/press/2023/0523_001.html", "2023-05-23", "html"),
    ("SC-BIS-2024-12-02", "https://www.bis.gov/press-release/commerce-strengthens-export-controls-restrict-chinas-capability-produce-advanced-semiconductors-military", "2024-12-02", "html"),
    ("SC-BIS-2026-01-13", "https://www.bis.gov/press-release/department-commerce-revises-license-review-policy-semiconductors-exported-china", "2026-01-13", "html"),
    ("SC-BIS-2025-05-13", "https://www.bis.gov/press-release/department-commerce-rescinds-biden-era-artificial-intelligence-diffusion-rule-strengthens-chip-related-export-controls", "2025-05-13", "html"),
    ("SC-SMIC-REPORTS-INDEX", "https://www.smics.com/en/site/company_financialSummary", None, "html"),
    ("SC-SMIC-2023-REPORTS-INDEX", "https://www.smics.com/en/site/company_financialSummary?year=2023", None, "html"),
    ("SC-SMIC-2024-REPORTS-INDEX", "https://www.smics.com/en/site/company_financialSummary?year=2024", None, "html"),
    ("SC-SMIC-2025-REPORTS-INDEX", "https://www.smics.com/en/site/company_financialSummary?year=2025", None, "html"),
    ("SC-SMIC-AR2022", "https://smic.cdn.shwebspace.com/uploads/SMIC 2022 Annual Report en.pdf", None, "pdf"),
    ("SC-SMIC-AR2023", "https://smic.cdn.shwebspace.com/uploads/66151b37/e00981.pdf", None, "pdf"),
    ("SC-SMIC-AR2024", "https://smic.cdn.shwebspace.com/uploads/67f6423d/e00981.pdf", None, "pdf"),
    ("SC-SMIC-FY2022-EARNINGS", "https://smic.cdn.shwebspace.com/uploads/63e4d9b4/Q422_EN.pdf", "2023-02-09", "pdf"),
    ("SC-SMIC-FY2023-EARNINGS", "https://smic.cdn.shwebspace.com/uploads/65c20820/ER-en.pdf", "2024-02-06", "pdf"),
    ("SC-SMIC-FY2024-EARNINGS", "https://smic.cdn.shwebspace.com/uploads/67ab0dc6/ER_EN.pdf", "2025-02-11", "pdf"),
    ("SC-SMIC-FY2025-EARNINGS", "https://smic.cdn.shwebspace.com/uploads/698ad7da/ER_EN.pdf", "2026-02-10", "pdf"),
]


def fetch_artifact(spec):
    source_id, url, public_date, extension = spec
    record = {"source_id": source_id, "url": url, "publication_date": public_date,
              "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
              "http_status": None, "status": "failed", "error": None,
              "sha256": None, "path": None, "bytes": 0,
              "freeze_eligible": bool(public_date and public_date <= FREEZE),
              "source_assessment": "requires_document_review"}
    try:
        response = requests.get(url, timeout=45, headers={"User-Agent": "Academic-research-replication/0.1 (public-records)"})
        record["http_status"] = response.status_code
        body = response.content
        if response.status_code != 200:
            record["error"] = f"HTTP {response.status_code}; not a source artifact"
            # Archive failure response separately so it can never be mistaken for law.
            fail_path = RAW / "failures" / f"{source_id}.{extension}.error"
            fail_path.parent.mkdir(parents=True, exist_ok=True)
            fail_path.write_bytes(body)
            record["failure_response_path"] = str(fail_path.relative_to(ROOT))
            return record
        digest = hashlib.sha256(body).hexdigest()
        path = RAW / f"{source_id}-{digest[:12]}.{extension}"
        # Content-addressed archives preserve revisions instead of overwriting them.
        if path.exists() and path.read_bytes() != body:
            raise RuntimeError("Content-address collision")
        path.write_bytes(body)
        record.update(status="retrieved", sha256=digest, path=str(path.relative_to(ROOT)), bytes=len(body))
    except requests.RequestException as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def acquire():
    RAW.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(MANIFEST).to_dict("records") if MANIFEST.exists() else []
    # Every Federal Register item is an original issued document, not today's
    # consolidated EAR. The statutory dates are parsed from the archived API.
    metadata_specs = [(f"SC-FR-{doc}-META", f"https://www.federalregister.gov/api/v1/documents/{doc}.json", None, "json") for doc in DOCUMENTS]
    with ThreadPoolExecutor(max_workers=5) as pool:
        records = list(pool.map(fetch_artifact, metadata_specs))
    text_specs = []
    for rec in records:
        if rec["status"] != "retrieved":
            continue
        obj = json.loads((ROOT / rec["path"]).read_text())
        rec["publication_date"] = obj["publication_date"]
        rec["freeze_eligible"] = obj["publication_date"] <= FREEZE
        rec["source_assessment"] = "original_issued_document_metadata"
        text_specs.append((rec["source_id"].replace("-META", "-TEXT"), obj["full_text_xml_url"], obj["publication_date"], "xml"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        records += list(pool.map(fetch_artifact, text_specs + OTHER_SOURCES))
    for rec in records:
        if rec["source_id"].startswith("SC-FR-") and rec["source_id"].endswith("-TEXT") and rec["status"] == "retrieved":
            rec["source_assessment"] = "original_issued_legal_text"
        if rec["status"] == "retrieved" and rec["path"].endswith((".xml", ".html")):
            text = BeautifulSoup((ROOT / rec["path"]).read_bytes(), "html.parser").get_text("\n", strip=True)
            (RAW / (rec["source_id"] + ".extracted.txt")).write_text(text)
        if rec["status"] == "retrieved" and rec["path"].endswith(".pdf"):
            subprocess.run(["pdftotext", "-layout", str(ROOT / rec["path"]), str(RAW / (rec["source_id"] + ".extracted.txt"))], check=True)
    # Preserve attempts as append-only rows, including meaningful retry history.
    pd.DataFrame(existing + records).to_csv(MANIFEST, index=False)
    return records


def _source(source_id):
    manifest = pd.read_csv(MANIFEST)
    found = manifest.loc[manifest.source_id.eq(source_id) & manifest.status.eq("retrieved")]
    if found.empty:
        # Archived systematic discovery sources are originals too. Keep their
        # existing content-addressed paths and identities instead of copying or
        # pretending to have performed another download.
        lookup = source_id.replace("SC-FR-", "LEGAL-DOC-")
        log = ROOT/"metadata/legal_discovery_acquisitions.jsonl"
        discoveries = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        candidates = [row for row in discoveries if row["source_id"] == lookup and row["status"] == "downloaded"]
        if not candidates:
            raise ValueError(f"Missing acquired primary source: {source_id}")
        row = pd.Series(candidates[-1])
        row["path"] = row["archive_path"]
    else:
        row = found.iloc[-1]
    if hashlib.sha256((ROOT / row.path).read_bytes()).hexdigest() != row.sha256:
        raise ValueError("Source checksum mismatch")
    return row


def build_legal_events():
    """Map manually reviewed original event scopes to immutable source records.

    This corpus is an event chronology. The record status refers to enactment,
    and does not certify a complete consolidated legal regime at the freeze.
    """
    adjudications_path = ROOT / "codebooks/semiconductor_legal_adjudications.csv"
    if not adjudications_path.exists():
        return
    records, claims = [], []
    for coded in pd.read_csv(adjudications_path).fillna("").to_dict("records"):
        source = _source(coded["source_id"])
        if Path(source.path).suffix.lower() == ".xml":
            from weaponized.semiconductors.legal import issued_xml_text
            text = issued_xml_text((ROOT/source.path).read_bytes(), coded["document_number"])
        else:
            text = verified_original_text(ROOT/source.path, source.sha256)
        if coded["required_text"] not in re.sub(r"\s+", " ", text):
            raise RuntimeError(f"Reviewed claim text missing from {source.source_id}: {coded['required_text']}")
        date_support = coded.get("effective_date_support", "")
        if date_support and date_support not in re.sub(r"\s+", " ", text):
            raise RuntimeError(f"Effective-date support absent for {coded['claim_id']}")
        document_number = coded["document_number"]
        if document_number:
            meta = json.loads((ROOT / _source(f"SC-FR-{document_number}-META").path).read_text())
            publication = meta["publication_date"]
            filing = re.search(r"\[FR Doc\. [^\]]+ Filed (\d{1,2}-\d{1,2}-\d{2});", text)
            info_public = datetime.strptime(filing.group(1), "%m-%d-%y").date().isoformat() if filing else publication
            citation = meta["citation"]
        else:
            publication = coded["publication_date"]
            info_public = publication
            citation = coded["legal_citation"]
        row = {column: None for column in LEGAL_COLUMNS}
        row.update(policy_id=coded["policy_id"], instrument_id=coded["policy_id"] + "-" + coded["phase_id"],
                   version_id=coded["policy_id"] + "-" + coded["phase_id"] + "-v1", jurisdiction=coded["jurisdiction"],
                   issuer="Bureau of Industry and Security" if coded["jurisdiction"] == "US" else "Ministerie van Buitenlandse Zaken",
                   official_language="en" if coded["jurisdiction"] == "US" else "nl", publication_date=publication,
                   effective_date=coded["effective_date"] or None, end_date=coded["end_date"] or None,
                   info_public_date=info_public, retrieval_timestamp=source.retrieval_timestamp, sha256=source.sha256,
                   technology_layer=coded["technology_layer"], product_code=coded["product_code"], legal_citation=citation,
                   destination=coded["destination"], end_user=coded["end_user"], end_use=coded["end_use"],
                   person_scope=coded["person_scope"], license_requirement=coded["license_requirement"],
                   review_presumption=coded["review_presumption"], exemption=coded["exemption"], status=coded["status"],
                   severity_ordinal=float(coded["severity_ordinal"]) if coded["severity_ordinal"] != "" else None,
                   confidence="single_coder_primary_text_verified", source_id=coded["source_id"],
                   adjudication_id=coded["claim_id"], evidence_verified=True)
        row.update(event_type=coded["event_type"], compliance_date=coded["compliance_date"] or None,
                   source_locator=coded["source_locator"], first_public_clock_basis="earliest_verified_FR_filing_or_official_publication",
                   current_law_consolidation_verified=False)
        if info_public > FREEZE or publication > FREEZE:
            raise RuntimeError("Post-freeze legal observation rejected")
        records.append(row)
        claims.append({"claim_id": coded["claim_id"], "source_id": coded["source_id"], "source_sha256": source.sha256,
                       "source_locator": coded["source_locator"], "claim": coded["claim"], "exact_supporting_text": coded["required_text"],
                       "event_date": coded["effective_date"], "info_public_date": info_public, "independent_second_coder": False})
    frame = pd.DataFrame(records)
    validate_legal_events(frame)
    frame.to_csv(PROCESSED / "legal_events.csv", index=False)
    pd.DataFrame(claims).to_csv(PROCESSED / "legal_claims.csv", index=False)
    frame.to_csv(OUTPUT / "historical_legal_chronology.csv", index=False)
    # Publication and effective dates appear separately; phased rules are not
    # collapsed into one false implementation date.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plot = frame.loc[frame.event_type.ne("administrative_comment_extension")].copy()
    fig, ax = plt.subplots(figsize=(10.0, max(5.0, len(plot) * .23)))
    for index, row in enumerate(plot.itertuples()):
        public, effect = pd.Timestamp(row.info_public_date), pd.Timestamp(row.effective_date)
        ax.plot([public, effect], [index, index], color="#888888", lw=1)
        ax.scatter([public], [index], marker="o", c="#2d6b8a", s=20, label="First verified public date" if index == 0 else None)
        ax.scatter([effect], [index], marker="|", c="#aa4a26", s=75, label="Legal effective date" if index == 0 else None)
    ax.set_yticks(range(len(plot)), [f"{r.jurisdiction} {r.policy_id.replace('SC-', '')}/{r.instrument_id.rsplit('-', 1)[-1]}" for r in plot.itertuples()], fontsize=7)
    ax.set_title("Primary-source control chronology: selected verified instruments")
    ax.set_xlabel("Dates from original records; event corpus, not a complete current-law code")
    ax.legend(loc="lower right", fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(OUTPUT / f"legal_chronology.{ext}", dpi=220)
    plt.close(fig)


def build_financial_inputs():
    """Extract a transparent descriptive series; no causal/control-state claim."""
    dates = {2022: "2023-02-09", 2023: "2024-02-06", 2024: "2025-02-11", 2025: "2026-02-10"}
    observations = []
    for year, public in dates.items():
        source_id = f"SC-SMIC-FY{year}-EARNINGS"
        if not MANIFEST.exists() or source_id not in set(pd.read_csv(MANIFEST).source_id):
            continue
        source = _source(source_id)
        original = verified_original_text(ROOT/source.path, source.sha256)
        normalized = re.sub(r"\s+", " ", original)
        display_date = datetime.strptime(public, "%Y-%m-%d").strftime("%B %-d, %Y")
        if display_date not in normalized:
            raise RuntimeError("Company release publication date not supported on page 1")
        patterns = {
            "annual_capital_expenditure": (rf"[Cc]apital expenditure[s]? in {year} was \$([0-9.]+) billion", 1e9, "USD_billion", "annual"),
            "fourth_quarter_rd_expense": (r"Research and development expenses\s+([0-9,]+)", 1e3, "USD_thousand", "quarter"),
        }
        for variable, (pattern, scale, unit, period) in patterns.items():
            match = re.search(pattern, normalized)
            if not match:
                raise RuntimeError(f"Source parsing failure for {source_id}:{variable}")
            native = float(match.group(1).replace(",", ""))
            # Locate the unnormalized first occurrence to count actual PDF pages.
            keyword = "Research and development expenses" if period == "quarter" else f"in {year} was"
            position = original.find(keyword)
            page = original[:position].count("\f") + 1 if position >= 0 else None
            observations.append({"observation_id": f"{source_id}:{variable}", "firm_id": "SMIC", "year": year,
                                 "variable": variable, "period_frequency": period, "valid_date": f"{year}-12-31",
                                 "info_public_date": public, "native_value": native, "native_unit": unit,
                                 "value_USD": native * scale, "price_basis": "nominal_not_inflation_adjusted",
                                 "source_id": source_id, "source_sha256": source.sha256,
                                 "source_locator": f"PDF p.{page}; {match.group(0)}",
                                 "financial_status": "reported_in_unaudited_earnings_release",
                                 "qualifying_capability_evidence": False, "causal_effect": False,
                                 "independent_second_coder": False})
    panel = pd.DataFrame(observations)
    panel.to_csv(PROCESSED / "reported_financial_inputs.csv", index=False)
    panel.to_csv(OUTPUT / "reported_financial_inputs.csv", index=False)
    if panel.empty:
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
    for ax, variable, divisor, ylabel in zip(axes, ["annual_capital_expenditure", "fourth_quarter_rd_expense"], [1e9, 1e6], ["Annual capital expenditure (USD billion)", "Q4 R&D expense (USD million)"]):
        subset = panel.loc[panel.variable.eq(variable)]
        ax.bar(subset.year, subset.value_USD / divisor, color="#2d6b8a")
        ax.set_ylabel(ylabel)
        ax.set_xticks(subset.year)
        ax.set_ylim(0, subset.value_USD.max() / divisor * 1.18)
        for row in subset.itertuples():
            ax.text(row.year, row.value_USD / divisor * 1.02, f"{row.value_USD / divisor:g}", ha="center", fontsize=8)
    fig.suptitle("SMIC reported investment inputs: descriptive, not substitution effects", fontsize=11)
    fig.text(.5, .01, "Primary company earnings releases; nominal USD. Annual capex and Q4 R&D have different measurement windows.", ha="center", fontsize=7)
    fig.tight_layout(rect=[0, .055, 1, .95])
    for ext in ["pdf", "png"]:
        fig.savefig(OUTPUT / f"smic_reported_inputs.{ext}", dpi=220)
    plt.close(fig)


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def build():
    for directory in [PROCESSED, OUTPUT]:
        directory.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((ROOT / "configs/semiconductors.yaml").read_text())
    if MANIFEST.exists():
        build_legal_events()
        build_financial_inputs()
    evidence_path = PROCESSED / "capability_evidence.csv"
    if not evidence_path.exists():
        pd.DataFrame(columns=EVIDENCE_COLUMNS).to_csv(evidence_path, index=False)
    evidence = pd.read_csv(evidence_path)
    legal_path = PROCESSED / "legal_events.csv"
    if not legal_path.exists():
        pd.DataFrame(columns=LEGAL_COLUMNS).to_csv(legal_path, index=False)
    rules = pd.read_csv(legal_path)
    validate_legal_events(rules)
    states = estimate_semiconductor_states(evidence, rules, config["target_version"], config)
    states.layers.to_csv(OUTPUT / "separate_capability_access.csv", index=False)
    summary = {"freeze": FREEZE, "label": "empirical_evidence_availability_audit",
               "aggregate": states.aggregate, "diagnostics": states.diagnostics,
               "identification": identification_feasibility(pd.DataFrame()),
               "verified_legal_event_rows": len(rules),
               "capability_scores_are_empirical_estimates": False,
               "no_numeric_national_capability_inferred_from_legal_rules": True}
    (OUTPUT / "summary.json").write_text(json.dumps(_json_safe(summary), indent=2, allow_nan=False) + "\n")
    schedule = []
    for origin in ["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]:
        for months in [6, 12, 24]:
            # No target-matched released outcomes are in the source corpus.
            row = forecast_availability(origin, months, None, config["target_version"], config["target_version"], freeze=FREEZE)
            row["horizon_months"] = months
            row["reasons"] = ";".join(row["reasons"])
            schedule.append(row)
    pd.DataFrame(schedule).to_csv(OUTPUT / "forecast_availability.csv", index=False)
    checks = []
    if MANIFEST.exists():
        manifest = pd.read_csv(MANIFEST)
        for rec in manifest.loc[manifest.status.eq("retrieved")].to_dict("records"):
            actual = hashlib.sha256((ROOT / rec["path"]).read_bytes()).hexdigest()
            checks.append({"source_id": rec["source_id"], "sha256_valid": actual == rec["sha256"], "source_date_known": pd.notna(rec["publication_date"])})
        if any(not item["sha256_valid"] for item in checks):
            raise RuntimeError("Source artifact checksum mismatch")
    pd.DataFrame(checks, columns=["source_id", "sha256_valid", "source_date_known"]).to_csv(OUTPUT / "source_integrity.csv", index=False)
    print(json.dumps(_json_safe(summary), indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="Acquire public primary source bytes; otherwise offline")
    args = parser.parse_args()
    if args.fetch:
        results = acquire()
        print(json.dumps({"retrieved": sum(r["status"] == "retrieved" for r in results), "failed": sum(r["status"] != "retrieved" for r in results)}))
    build()
