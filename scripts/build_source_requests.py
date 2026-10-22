"""Generate actionable source requests without admitting unavailable contents.

This is a provenance-checked acquisition checklist, not an empirical dataset.
Four SEC pointers are re-derived from immutable archived submission metadata.
Other pointers retain the exact failed-log provenance and unresolved public clock.
"""
from pathlib import Path
from urllib.parse import urlparse
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    book=json.loads((ROOT/'codebooks/priority_source_requests.json').read_text())
    sources={r['source_id']:r for r in json.loads((ROOT/'metadata/source_registry.json').read_text())}
    rows=[];submission_checks=0
    for spec in book['requests']:
        log=ROOT/spec['log'];raw=log.read_bytes()
        found=[(i,json.loads(line)) for i,line in enumerate(raw.decode().splitlines(),1) if json.loads(line).get('source_id')==spec['source_id']]
        if not found:raise ValueError(f"Missing logged request:{spec['source_id']}")
        line_no,entry=found[-1]
        if entry['status'] not in {'failed','blocked'}:raise ValueError('Request already has available content; review before retaining as blocker')
        url=entry['url']
        if urlparse(url).scheme!='https':raise ValueError('Public original source must have an explicit HTTPS URL')
        row=dict(rank=spec['rank'],source_id=spec['source_id'],label=spec['label'],url=url,
                 latest_logged_status=entry['status'],latest_attempt_timestamp=entry['retrieval_timestamp'],
                 failure_manifest=spec['log'],failure_manifest_sha256=hashlib.sha256(raw).hexdigest(),failure_manifest_line=line_no,
                 verified_submission_filing_date='',discovery_source_id='',discovery_source_sha256='',discovery_locator='',
                 file_contents_available=False,historical_contents_admitted=False,reason=spec['reason'])
        if spec.get('discovery_submission'):
            source=sources[spec['discovery_submission']];body=(ROOT/source['archive_path']).read_bytes()
            if hashlib.sha256(body).hexdigest()!=source['sha256']:raise ValueError('Discovery submission bytes changed')
            metadata=json.loads(body);recent=metadata['filings']['recent']
            idx=[i for i,x in enumerate(recent['accessionNumber']) if x==spec['accession']]
            if len(idx)!=1:raise ValueError('Ambiguous or absent accession in original submission snapshot')
            i=idx[0];date=recent['filingDate'][i]
            if not date<=book['freeze'] or recent['form'][i]!='10-Q':raise ValueError('Post-freeze or wrong-form discovery pointer')
            expected=f"https://www.sec.gov/Archives/edgar/data/{int(metadata['cik'])}/{spec['accession'].replace('-','')}/{recent['primaryDocument'][i]}"
            if expected!=url or entry.get('publication_date')!=date:raise ValueError('URL/date disagrees with immutable submission metadata')
            row.update(verified_submission_filing_date=date,discovery_source_id=source['source_id'],discovery_source_sha256=source['sha256'],
                       discovery_locator=f"filings.recent[{i}]:accessionNumber,form,filingDate,primaryDocument")
            submission_checks+=1
        rows.append(row)
    if len({r['source_id'] for r in rows})!=len(rows) or sorted(r['rank'] for r in rows)!=list(range(1,len(rows)+1)):
        raise ValueError('Request keys/ranks must be unique and contiguous')
    target=ROOT/'metadata/priority_source_requests.csv'
    with target.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    doc=['# Inputs that would unblock the next research session','',
         'The current repository can be continued without action from you. The most useful additional help is obtaining the public originals below. The first four requests are the highest priority. Download the complete original HTML or PDF, keep its source URL, and attach it with your next prompt. For PDFs, provide the original file rather than a screenshot or summary. Public-source uploads need no private-account credentials or paid service.', '',
         'These are missing-source requests, not admitted observations. Four filing dates/URLs are independently re-derived from archived SEC submission bytes; that verifies the filing pointer, not the unavailable filing contents or historical byte identity. Other dates remain pending original review. Every supplied file will be hashed, archived and checked for identity, source/publication clocks and the October 11, 2026 information cutoff before scientific use.', '',
         '| Priority | Original | What it can help resolve |','|---|---|---|']
    doc += [f"| {r['rank']} | [{r['label']}]({r['url']}) | {r['reason']} |" for r in rows]
    doc += ['', '## Access and remaining measurements','',
            'A current-session probe of a formerly accessible SEC metadata host failed at the proxy with CONNECT 403 (`metadata/continuation_access_probe.jsonl`). Previously saved environment-domain settings are not proof that the live policy was applied. If you control the cloud environment, an applied working public-source network configuration may remove the need for manual uploads. Do not send credentials, disable TLS checks or use a private account on this project’s behalf.', '',
            'If only a few files are practical, supply MP’s Q2 filing and technical report, followed by the Energy Fuels and USA Rare Earth Q2 filings. These documents may advance measurement; they do not by themselves complete the physical network or justify forecast probabilities.', '',
            'The strongest further inputs are dated element/product inventories and stock-flow movements; Nd/Pr/Dy/Tb assays and operating recoveries; metal/alloy/magnet recipes, qualified throughput and routing/input-origin records; bloc/grade demand; and a representative project cohort with verified entries/exits and observation coverage. Semiconductor target/yield/tool-origin/access measurements, historical disclosure obligations, independent coders and specialist review remain separate requirements. Four annual-report release clocks also remain unresolved: Iluka FY2025 and Pensana FY2023–2025 need dated release records, not signatures or filenames.', '',
            'The complete executable blocker list is `audit/remaining_requirements.md`. No upload, expert review or environment change is required simply to prompt another continuation; the listed inputs determine which blocked empirical milestones can advance.','']
    (ROOT/'docs/INPUTS_NEEDED.md').write_text('\n'.join(doc))
    result=dict(passed=True,classification=book['classification'],requests=len(rows),immutable_submission_pointer_checks=submission_checks,
                unavailable_contents_read_or_admitted=0,new_empirical_observations=0,empirical_forecasts_unblocked=False,
                evidence='metadata/priority_source_requests.csv',user_actions='docs/INPUTS_NEEDED.md')
    (ROOT/'outputs/diagnostics/source_request_readiness.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
