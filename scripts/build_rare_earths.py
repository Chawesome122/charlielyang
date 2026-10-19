#!/usr/bin/env python3
"""Extract selected primary observations; never infer a complete global risk set."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import date
import pandas as pd
from bs4 import BeautifulSoup
from weaponized.io.archive import sha256_file
from weaponized.io.original_text import verified_original_text
from weaponized.io.schemas import Claim

ROOT = Path(__file__).resolve().parents[1]
FREEZE = "2026-10-11"


def normalize(text):
    return " ".join(text.replace("\u200b", "").split())


def main():
    records = [json.loads(line) for line in (ROOT/"metadata/rare_earth_acquisitions.jsonl").read_text().splitlines()]
    sources = {}
    for record in records:
        if record["status"] == "downloaded":
            sources[record["source_id"]] = record
    # Read actual SEC metadata, not dates guessed from the fiscal year or URL.
    filing_dates = {}
    for sid, record in sources.items():
        if sid.endswith("SUBMISSIONS") and sid != "RE-MOLYCORP-SUBMISSIONS":
            obj = json.loads((ROOT/record["archive_path"]).read_text())
            recent = obj["filings"]["recent"]
            for i, document in enumerate(recent.get("primaryDocument", [])):
                acc = recent["accessionNumber"][i].replace("-", "")
                filing_dates[(acc, document)] = recent["filingDate"][i]
    for sid, record in sources.items():
        match = re.search(r"/([0-9]{18})/([^/]+)$", record["url"])
        if match and match.groups() in filing_dates:
            record["publication_date"] = filing_dates[match.groups()]
    observations, extraction_log = [], []

    def add(sid, entity, variable, value, unit, basis, valid, locator, quote="", event_kind="observed"):
        source = sources[sid]
        public = source.get("publication_date")
        if public is None or public > FREEZE:
            raise ValueError(f"No eligible first-public date for {sid}")
        obs_id = f"{entity}:{variable}:{valid}"
        row = Claim(observation_id=obs_id, record_version_id=f"{obs_id}:{sid}", entity_id=entity,
                    variable=variable, value=value, native_unit=unit, product_basis=basis,
                    valid_date=valid, info_public_date=public, source_id=sid,
                    source_sha256=source["sha256"], locator=locator, evidence_class="empirical",
                    event_kind=event_kind,
                    missing_reason="source marks period not applicable" if value is None else None).model_dump(mode="json")
        row.update(quote=quote, independent_corroboration=False, observation_status="company-reported",
                   public_date_basis="verified source filing/publication; conservative availability, not search-certified earliest release")
        observations.append(row)

    # Extract entire published KPI row versions, including restatements/repeated history.
    for year in [2022, 2023, 2024, 2025]:
        sid = f"RE-MP-10K{year}"
        if sid not in sources:
            continue
        source = sources[sid]
        soup = BeautifulSoup((ROOT/source["archive_path"]).read_text(), "html.parser")
        for table_index, table in enumerate(soup.find_all("table")):
            text = normalize(table.get_text(" ", strip=True))
            if len(text) > 15000 or not re.search(r"REO Production Volume", text, re.I):
                continue
            is_quarterly = bool(re.search(r"FY" + str(year), text))
            if not is_quarterly and "Year ended December 31" not in text:
                continue
            for tr in table.find_all("tr"):
                row_text = normalize(tr.get_text(" ", strip=True))
                for label, entity, variable, basis in [
                    (r"REO Production Volume", "MP_MountainPass_mine", "reported_output", "total_REO_content_in_concentrate"),
                    (r"NdPr Production Volume", "MP_MountainPass_separation", "reported_output", "finished_packaged_NdPr_oxide"),
                ]:
                    match = re.search(label + r"\s*\(MTs\)\s*(.*)$", row_text, re.I)
                    if not match:
                        continue
                    n = 12 if is_quarterly else 3
                    tokens = re.findall(r"[\d,]+|N/A|—", match[1])[:n]
                    if len(tokens) != n:
                        raise ValueError(f"KPI extraction length error {sid}: {row_text}")
                    for i, token in enumerate(tokens):
                        y = year - i // 4 if is_quarterly else year - i
                        q = 4 - i % 4 if is_quarterly else 4
                        valid = str(pd.Period(f"{y}Q{q}", freq="Q").end_time.date())
                        value = None if token == "N/A" else 0.0 if token == "—" else float(token.replace(",", ""))
                        add(sid, entity, variable + ("_quarter" if is_quarterly else "_year"), value,
                            "metric_tonnes_per_observed_quarter" if is_quarterly else "metric_tonnes_per_observed_year",
                            basis, valid, f"HTML table {table_index}; row {label}; column {i+1}", row_text)
                    extraction_log.append(dict(source_id=sid, table_index=table_index, row=row_text, observations=n))

    # Fixed exact-source statement extractions. Values are guarded by matched text.
    statement_specs = [
        ("RE-EF-10K2024", "EF_WhiteMesa_separation", "reported_output_year", 38,
         "metric_tonnes_per_observed_year", "separated_NdPr_oxide", "2024-12-31",
         r"produced 38 tonnes of separated NdPr during 2024"),
        ("RE-EF-10K2024", "EF_WhiteMesa_separation", "nameplate_low", 800,
         "metric_tonnes_per_year", "separated_NdPr_oxide", "2024-12-31",
         r"produce up to 800.{0,8}1,000 metric tons"),
        ("RE-EF-10K2024", "EF_WhiteMesa_separation", "nameplate_high", 1000,
         "metric_tonnes_per_year", "separated_NdPr_oxide", "2024-12-31",
         r"produce up to 800.{0,8}1,000 metric tons"),
    ]
    for sid, entity, variable, value, unit, basis, valid, pattern in statement_specs:
        if sid not in sources:
            continue
        soup = BeautifulSoup((ROOT/sources[sid]["archive_path"]).read_text(), "html.parser")
        for el in soup.select("script,style,ix\\:header"):
            el.decompose()
        text = normalize(soup.get_text(" ", strip=True))
        match = re.search(pattern, text, re.I)
        if not match:
            raise ValueError(f"Statement evidence did not match: {sid}: {pattern}")
        quote = text[max(0, match.start()-100):match.end()+180]
        add(sid, entity, variable, value, unit, basis, valid, f"Item 1, White Mesa Phase 1; regex {pattern}", quote)
    # IEA publication date is established by its report landing page, separate from
    # live navigation. No assertion that the entire live page was frozen in April.
    if "RE-IEA2026" in sources and "RE-IEA2026-REPORT" in sources:
        report = normalize(verified_original_text(ROOT/sources["RE-IEA2026-REPORT"]["archive_path"], sources["RE-IEA2026-REPORT"]["sha256"]))
        if "Published 08 April 2026" not in report:
            raise ValueError("IEA original publication date not verified")
        sources["RE-IEA2026"]["publication_date"] = "2026-04-08"
        text = normalize(verified_original_text(ROOT/sources["RE-IEA2026"]["archive_path"], sources["RE-IEA2026"]["sha256"]))
        for variable, value, word in [("mining_share",0.60,"60%"),("refining_share",0.91,"91%"),("sintered_magnet_share",0.94,"94%")]:
            pos = text.find(word)
            if pos < 0:
                raise ValueError(f"IEA stated share absent: {word}")
            add("RE-IEA2026", "China_magnet_REE", variable, value, "fraction_global_output",
                "magnet_REE_stage_specific", "2024-12-31", f"Executive summary; China stage shares; literal {word}", text[max(0,pos-220):pos+250])
            observations[-1].update(observation_status="IEA-reported approximate share", independent_corroboration=False,
                                    historical_vintage_caveat="Original report dated 2026-04-08; retrieved live summary includes later navigation. Only report-body claim retained, not certified April web snapshot.")
    output = ROOT/"data/processed/rare_earths"
    output.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(observations)
    frame.to_csv(output/"observations.csv", index=False)
    (output/"extraction_log.json").write_text(json.dumps(extraction_log, indent=2))
    # Keep repeated source versions: only the view below de-duplicates for reporting.
    from weaponized.io.vintages import select_asof
    latest = select_asof(frame, FREEZE)
    latest.to_csv(output/"observations_asof_freeze.csv", index=False)
    (output/"source_index.json").write_text(json.dumps(sources, indent=2))
    summary = dict(freeze=FREEZE, versioned_observations=len(frame), latest_observations=len(latest),
                   downloaded_artifacts=len(sources), artifacts_used_for_observations=int(frame.source_id.nunique()),
                   observed_project_universe="selected documented subset, not a statistical risk set",
                   empirical_service="BLOCKED: recipes, full supplier routes, target-grade demand, inventories and qualification evidence missing",
                   forecast="BLOCKED: no calibrated risk set and no validated empirical network",
                   failed_acquisitions=sum(r["status"]=="failed" for r in records))
    (ROOT/"outputs/empirical/rare_earths").mkdir(parents=True, exist_ok=True)
    (ROOT/"outputs/empirical/rare_earths/summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
