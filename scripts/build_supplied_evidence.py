"""Offline admission/extraction of user-supplied public-source PDF copies."""
from datetime import datetime
import csv
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from weaponized.io.original_text import verified_original_text
from weaponized.io.supplied_evidence import extract_claim, one_match, source_pages, incorporated_report_link
from weaponized.semiconductors.supplied_operations import parse_quarterly_release

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/processed/supplied_evidence"


def build():
    book=json.loads((ROOT/"codebooks/supplied_evidence.json").read_text())
    sources=json.loads((ROOT/"metadata/user_supplied_sources.json").read_text())
    index={r["source_id"]:r for r in sources}
    old=json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    requests=json.loads((ROOT/"codebooks/priority_source_requests.json").read_text())["requests"]
    clocks=[];parsed={}
    for s in sources:
        pages=source_pages(ROOT,s);parsed[s["source_id"]]=pages
        identity=one_match(s["identity_pattern"],pages[s["identity_page"]-1])[0]
        if s["info_public_date"]>book["freeze"]:raise ValueError("Post-freeze upload content")
        rank=s["request_rank"];proof="";proof_sha="";proof_page=None
        if rank in [1,3,4,5]:
            req=next(r for r in requests if r["rank"]==rank)
            sub=old[req["discovery_submission"]];body=(ROOT/sub["archive_path"]).read_bytes()
            if hashlib.sha256(body).hexdigest()!=sub["sha256"]:raise ValueError("Submission bytes changed")
            sec=json.loads(body);recent=sec["filings"]["recent"]
            i=recent["accessionNumber"].index(req["accession"])
            expected=f"https://www.sec.gov/Archives/edgar/data/{int(sec['cik'])}/{req['accession'].replace('-','')}/{recent['primaryDocument'][i]}"
            if expected!=s["source_url"] or recent["filingDate"][i]!=s["info_public_date"] or recent["reportDate"][i]!="2026-06-30" or recent["form"][i]!="10-Q":
                raise ValueError("Filing date, accession, form or report period disagrees with independent SEC bytes")
            proof=f"{req['discovery_submission']}:filings.recent[{i}]";proof_sha=sub["sha256"]
            if "June 30, 2026" not in pages[0] or s["source_url"] not in pages[0]:raise ValueError("Wrong filing period/printed URL")
        elif rank in [2,6,7]:
            parent=old["RE-MP-10K2025" if rank==2 else "RE-EF-10K2025"]
            body=(ROOT/parent["archive_path"]).read_bytes()
            if hashlib.sha256(body).hexdigest()!=parent["sha256"]:raise ValueError("Parent bytes changed")
            label=incorporated_report_link(body,parent['url'],s['source_url'])
            if parent["publication_date"]!=s["info_public_date"]:
                raise ValueError("Incorporated report link/date not supported")
            if s["source_url"] not in pages[0]:raise ValueError("Wrong technical report printed URL")
            proof=parent["source_id"]+":full incorporated URL; "+label+"; conservative public-by date, not earliest release"
            proof_sha=parent["sha256"]
        elif rank in [8,9]:
            display=datetime.strptime(s["info_public_date"],"%Y-%m-%d").strftime("%B %-d, %Y")
            proof=one_match(r"Shanghai, China –\s*"+re.escape(display)+r" – Semiconductor Manufacturing International Corporation",pages[0])[0]
            proof_sha=s["sha256"];proof_page=1
        elif rank==10:
            proof=one_match(r"Friday, November 1, 2024",pages[0])[0]
            one_match(r"\[FR Doc\. 2024–25411 Filed 10–30–24; 8:45 am\]",pages[18])
            proof_sha=s["sha256"];proof_page=1
        elif rank==11:
            proof=one_match(r"\[FR Doc\. 2025-05427 Filed: 3/25/2025 4:30 pm; Publication Date: 3/28/2025\]",pages[12])[0]
            proof_sha=s["sha256"];proof_page=13
        else:raise ValueError("Unreviewed request identity")
        clocks.append(dict(source_id=s["source_id"],request_source_id=s["request_source_id"],request_rank=rank,
                           source_sha256=s["sha256"],archive_path=s["archive_path"],source_url=s["source_url"],
                           identity_quote=identity,identity_pdf_page=s["identity_page"],info_public_date=s["info_public_date"],
                           public_clock_method=s["public_clock_method"],public_clock_proof=proof,public_clock_proof_sha256=proof_sha,
                           public_clock_pdf_page=proof_page,representation=s["representation"],
                           historical_byte_vintage_certified=False,earliest_public_date_certified=False,
                           successful_HTTP_acquisition_claimed=False,passed=True))
    claims=[extract_claim(parsed[r["source_id"]],r,index[r["source_id"]]) for r in book["claims"]]
    if len({r['claim_id'] for r in claims})!=len(claims):raise ValueError("Duplicate supplied claim")
    smic=[]
    for spec in book["smic_sources"]:
        s=index[spec["source_id"]];smic+=parse_quarterly_release(parsed[s["source_id"]],spec,s)
    OUT.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(clocks).to_csv(OUT/"source_admissions.csv",index=False)
    pd.DataFrame(claims).to_csv(OUT/"claims.csv",index=False)
    pd.DataFrame(smic).to_csv(OUT/"smic_quarterly_versions.csv",index=False)
    # XML quality flags are compared with the published PDF, not silently fixed.
    p24=next(parsed[s["source_id"]] for s in sources if s["request_rank"]==10)
    legal=[dict(document="2024-25411",check="published_insertion_marker",pdf_page=i+1,
                count=page.count("[INSERT FR PAGE"),finding="present_in_published_pdf_not_just_XML",passed=True)
           for i,page in enumerate(p24) if "[INSERT FR PAGE" in page]
    if not legal:raise ValueError("Expected published insertion markers not found")
    legal.append(dict(document="2024-25411",check="embedded_address_date",pdf_page=5,count=1,
                      finding="present_in_published_pdf; source text retained",passed="EaseyNovember 1," in p24[4] and "2024 Commercial Building" in p24[4]))
    legal.append(dict(document="2025-05427",check="reported_filing_clock",pdf_page=13,count=1,
                      finding="filed March 25 2025 16:30; published March 28; no globally earliest public clock inferred",passed=True))
    pd.DataFrame(legal).to_csv(OUT/"legal_pdf_correspondence.csv",index=False)
    result=dict(passed=all(r['passed'] for r in clocks+legal),freeze=book['freeze'],sources=len(sources),
                requested_sources=len(requests),unfulfilled_request_ranks=sorted(set(r['rank'] for r in requests)-set(s['request_rank'] for s in sources)),source_identity_clock_checks=len(clocks),
                claims=len(claims),numerical_claims=sum(r['value'] is not None for r in claims),
                smic_native_cells=len(smic),legal_pdf_checks=len(legal),
                public_pdf_marker_occurrences=sum(r['count'] for r in legal if r['check']=='published_insertion_marker'),
                original_at_vintage_certified=False,empirical_service_identified=False,empirical_forecasts_unblocked=False,
                representative_transition_hazards_identified=False,semiconductor_target_capability_identified=False,
                missing='Original-at-vintage bytes and physical/target/risk/opacity gates remain unresolved; document admissions do not certify empirical adequacy')
    (ROOT/"outputs/diagnostics/supplied_evidence_validation.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=="__main__":build()
