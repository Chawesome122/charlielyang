"""Execute missing-release-clock, metadata-contamination and as-of masking audits."""
import json
import subprocess
from pathlib import Path

import pandas as pd

from weaponized.io.archive import sha256_file
from weaponized.io.publication import linked_publication_clock
from weaponized.io.publication_extension import report_link_metadata, source_vintage_readiness
from weaponized.io.vintages import select_asof, event_observed

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = json.loads((ROOT/"codebooks/publication_extension.json").read_text())
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    clocks = pd.read_csv(ROOT/"data/processed/finance_material/publication_clock_audit.csv").fillna("")
    out = ROOT/"data/processed/publication_extension"
    out.mkdir(parents=True, exist_ok=True)
    readiness, rejected, annuals = [], [], []
    for clock in clocks.to_dict("records"):
        sid = clock["source_id"]
        source, evidence = sources[sid], sources[clock["public_clock_source_id"]]
        for row in [source, evidence]:
            if sha256_file(ROOT/row["archive_path"]) != row["sha256"]:
                raise ValueError("Source or clock evidence checksum mismatch")
        html = (ROOT/evidence["archive_path"]).read_text()
        try:
            result = linked_publication_clock(html, evidence["url"], source["url"], clock["method"], spec["freeze"])
        except ValueError:
            if clock["status"] != "UNRESOLVED":
                raise
            public = None
        else:
            public = result["info_public_date"]
            if public != clock["info_public_date"] or clock["status"] != "RESOLVED":
                raise ValueError("Derived clock disagrees with independently re-executed evidence rule")
        for origin in spec["origins"]:
            readiness.append(dict(source_id=sid, source_sha256=source["sha256"],
                                  clock_source_id=evidence["source_id"], clock_source_sha256=evidence["sha256"],
                                  origin=origin, info_public_date=public,
                                  **source_vintage_readiness(public, source["retrieval_timestamp"], origin, spec["freeze"])))
        if sid not in spec["unresolved_annual_sources"]:
            continue
        details = report_link_metadata(html, evidence["url"], source["url"])
        if details["exact_report_link_count"] < 1 or public is not None:
            raise ValueError("Annual-report audit universe no longer matches unresolved exact links")
        info = subprocess.run(["pdfinfo", "-isodates", str(ROOT/source["archive_path"])],
                              check=True, text=True, capture_output=True).stdout
        metadata = dict(line.split(":", 1) for line in info.splitlines() if ":" in line)
        for field in ["CreationDate", "ModDate"]:
            if metadata.get(field):
                rejected.append(dict(source_id=sid, candidate_kind="PDF."+field,
                                     candidate_value=metadata[field].strip(), candidate_source_sha256=source["sha256"],
                                     admissible_as_publication=False,
                                     reason="Binary authoring metadata is not evidence of public distribution"))
        for item in details["rejected_page_date_candidates"]:
            rejected.append(dict(source_id=sid, candidate_kind=item["kind"], candidate_value=item["value"],
                                 candidate_source_sha256=evidence["sha256"], admissible_as_publication=False,
                                 reason="Generic reports-page date is not bound to the individual attachment"))
        rejected.append(dict(source_id=sid, candidate_kind="URL.filename_or_upload_directory",
                             candidate_value=source["url"], candidate_source_sha256=source["sha256"],
                             admissible_as_publication=False,
                             reason="Filename and upload-directory date tokens do not prove public availability"))
        annuals.append(dict(source_id=sid, source_sha256=source["sha256"],
                            report_url=source["url"], issuer_page_url=evidence["url"],
                            clock_source_sha256=evidence["sha256"], status="UNRESOLVED",
                            info_public_date=None, earliest_verified_availability_in_freeze=None,
                            **{k:json.dumps(v) if isinstance(v, list) else v for k,v in details.items()}))
    pd.DataFrame(readiness).to_csv(out/"source_origin_readiness.csv", index=False)
    pd.DataFrame(rejected).to_csv(out/"rejected_date_candidates.csv", index=False)
    pd.DataFrame(annuals).to_csv(out/"annual_clock_blockers.csv", index=False)
    claims = pd.read_csv(ROOT/"data/processed/finance_material/observations.csv")
    masking = []
    for origin in spec["origins"]:
        public = select_asof(claims, origin, keys=("observation_id",))
        completed = event_observed(claims, origin)
        naive = claims[pd.to_datetime(claims.valid_date) <= pd.Timestamp(origin)]
        not_public = naive[~naive.record_version_id.isin(public.record_version_id)]
        masking.append(dict(origin=origin, total_claim_versions=len(claims),
                            two_clock_information_available=len(public),
                            event_date_and_public_clock_available=len(completed),
                            naive_event_date_only_claims=len(naive),
                            event_date_only_lookahead_claims=len(not_public),
                            historical_byte_vintage_certified=False))
    pd.DataFrame(masking).to_csv(out/"claim_origin_masking.csv", index=False)
    attempts = [json.loads(x) for x in (ROOT/"metadata/publication_extension_acquisitions.jsonl").read_text().splitlines()]
    result = dict(passed=True, annual_reports_audited=len(annuals),
                  unresolved_annual_publication_dates=len(annuals), new_publication_dates_resolved=0,
                  rejected_auxiliary_date_candidates=len(rejected), source_origin_pairs=len(readiness),
                  origin_mask_checks=len(masking), actual_claim_versions=len(claims),
                  failed_new_official_index_requests=sum(x["status"]=="failed" for x in attempts),
                  successful_new_source_downloads=sum(x["status"]=="downloaded" for x in attempts),
                  original_at_vintage_byte_certificates=0, empirical_forecasts_generated=False,
                  unknown_dates_substituted=False, immutable_source_checks_passed=True)
    (ROOT/"outputs/diagnostics/publication_extension_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
