"""Systematic public Federal Register discovery, separate from reviewed coding.

Candidates never enter legal intensity/capability estimates merely because a
query matched. Search completeness is term-dependent; current law still needs
item-specific amendment/suspension adjudication.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
from weaponized.io.archive import fetch_source,append_record,sha256_file

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument("--fetch",action="store_true");parser.add_argument("--fetch-texts",action="store_true");args=parser.parse_args()
    log=ROOT/"metadata/legal_discovery_acquisitions.jsonl"
    queries=[]
    for i,term in enumerate(["semiconductor",'"advanced computing"'],1):
        parameters={"conditions[term]":term,"conditions[agencies][]":"industry-and-security-bureau",
                    "conditions[publication_date][gte]":"2022-01-01","conditions[publication_date][lte]":"2026-10-11",
                    "per_page":1000,"order":"oldest"}
        queries.append((f"LEGAL-DISCOVERY-{i}","https://www.federalregister.gov/api/v1/documents.json?"+urlencode(parameters)))
    if args.fetch:
        def fetch(item):return fetch_source(item[1],item[0],"data/raw/legal_discovery")
        for record in ThreadPoolExecutor(max_workers=2).map(fetch,queries):append_record(record,log)
    records=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    matched={};query_audit=[]
    for sid,url in queries:
        successes=[row for row in records if row["source_id"]==sid and row["status"]=="downloaded"]
        if not successes:
            query_audit.append(dict(source_id=sid,status="BLOCKED_NO_DOWNLOADED_QUERY"));continue
        record=successes[-1]
        if sha256_file(ROOT/record["archive_path"])!=record["sha256"]:raise ValueError("Query artifact checksum mismatch")
        response=json.loads((ROOT/record["archive_path"]).read_text())
        if response.get("next_page_url"):raise RuntimeError("Discovery pagination incomplete; do not claim full query traversal")
        query_audit.append(dict(source_id=sid,status="query_traversed",count=response["count"],sha256=record["sha256"]))
        for result in response["results"]:
            if result["publication_date"]>"2026-10-11":raise ValueError("Future public record in historical query")
            number=result["document_number"]
            row=matched.setdefault(number,dict(document_number=number,title=result["title"],publication_date=result["publication_date"],document_type=result["type"],url=result["html_url"],query_sources=[],status="DISCOVERY_ONLY_NOT_SCOPE_ADJUDICATED"))
            row["query_sources"].append(sid)
    reviewed=set(pd.read_csv(ROOT/"data/processed/semiconductors/legal_events.csv").policy_id.str.removeprefix("SC-US-"))
    if args.fetch_texts:
        known={row['source_id']:row for row in records if row['status']=='downloaded'}
        specs=[(f"LEGAL-DOC-{number}-META",f"https://www.federalregister.gov/api/v1/documents/{number}.json")
               for number in matched if number not in reviewed]
        def get(item):
            sid,url=item
            if sid in known:return known[sid]
            return fetch_source(url,sid,"data/raw/legal_discovery")
        metadata=list(ThreadPoolExecutor(max_workers=4).map(get,specs))
        text_specs=[]
        for record in metadata:
            if record['status']=='downloaded':
                content=json.loads((ROOT/record['archive_path']).read_text())
                if content['publication_date']>'2026-10-11':raise ValueError('Future issued document rejected')
                record['publication_date']=content['publication_date']
                text_specs.append((record['source_id'].replace('-META','-TEXT'),content['full_text_xml_url']))
            if record['source_id'] not in known:append_record(record,log)
        for record in ThreadPoolExecutor(max_workers=4).map(get,text_specs):
            if record['source_id'] not in known:append_record(record,log)
    # Enrich text archives with the original issued document's verified date.
    # Append enrichment rather than overwriting an earlier acquisition record.
    current=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    dates={row['source_id'].replace('-META','-TEXT'):row.get('publication_date') for row in current
           if row['source_id'].endswith('-META') and row['status']=='downloaded' and row.get('publication_date')}
    enriched={(row['source_id'],row.get('sha256'),row.get('publication_date')) for row in current}
    for row in current:
        if row['status']=='downloaded' and row['source_id'] in dates and not row.get('publication_date'):
            key=(row['source_id'],row.get('sha256'),dates[row['source_id']])
            if key in enriched:continue
            row=dict(row,publication_date=dates[row['source_id']],enrichment='public_date_from_corresponding_original_document_metadata')
            append_record(row,log)
            enriched.add(key)
    rows=[]
    for row in matched.values():
        row["query_sources"]=";".join(row["query_sources"])
        row["in_reviewed_event_corpus"]=row["document_number"] in reviewed
        row["status"]="IN_REVIEWED_EVENT_CORPUS" if row["in_reviewed_event_corpus"] else "NOT_IN_REVIEWED_EVENT_CORPUS"
        rows.append(row)
    target=ROOT/"data/processed/semiconductors/legal_discovery_candidates.csv"
    columns=['document_number','title','publication_date','document_type','url','query_sources','status','in_reviewed_event_corpus']
    pd.DataFrame(rows,columns=columns).sort_values(["publication_date","document_number"]).to_csv(target,index=False)
    report=dict(freeze="2026-10-11",queries=query_audit,unique_candidates=len(rows),
                reviewed_document_matches=sum(row["in_reviewed_event_corpus"] for row in rows),
                not_in_reviewed_event_corpus=sum(not row["in_reviewed_event_corpus"] for row in rows),
                completeness="Complete traversal of these two queries only, not a complete legal universe or consolidated law")
    refreshed=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    originals=[row for row in refreshed if row['source_id'].startswith('LEGAL-DOC-') and row['source_id'].endswith('-TEXT') and row['status']=='downloaded']
    verified_text_ids=set()
    for row in originals:
        if sha256_file(ROOT/row['archive_path'])!=row['sha256']:raise ValueError('Original legal text archive mismatch')
        payload=(ROOT/row['archive_path']).read_text(errors='replace')
        number=row['source_id'].removeprefix('LEGAL-DOC-').removesuffix('-TEXT')
        if 'xml' not in row.get('content_type','').lower() or number not in payload:
            raise ValueError('Downloaded response does not establish the original issued XML text')
        if row.get('publication_date') and row['publication_date']<='2026-10-11':verified_text_ids.add(row['source_id'])
    report['additional_original_issued_texts_acquired']=len(verified_text_ids)
    (ROOT/"outputs/diagnostics/legal_discovery_coverage.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
