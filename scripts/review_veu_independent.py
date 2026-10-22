from pathlib import Path
import hashlib,json,re
from datetime import datetime,timezone,date
import xml.etree.ElementTree as ET
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];book=json.loads((ROOT/'codebooks/veu_extension.json').read_text())
registry=pd.read_csv(ROOT/'metadata/semiconductor_sources.csv',keep_default_na=False).set_index('source_id')
clauses=pd.read_csv(ROOT/'data/processed/veu_extension/clauses.csv',keep_default_na=False)
events=pd.read_csv(ROOT/'data/processed/veu_extension/issued_events.csv',keep_default_na=False)
clocks=pd.read_csv(ROOT/'data/processed/veu_extension/source_clocks.csv',keep_default_na=False)
links=pd.read_csv(ROOT/'data/processed/veu_extension/permission_removal_links.csv',keep_default_na=False)
origins=pd.read_csv(ROOT/'data/processed/veu_extension/origin_phase_checks.csv',keep_default_na=False)
failures=[];checks=[];native={};source_hashes={}
def check(label,condition,evidence=None):
 row=dict(check=label,passed=bool(condition))
 if evidence is not None:row['evidence']=evidence
 checks.append(row)
 if not condition:failures.append(label)
def norm(element):return ' '.join(''.join(element.itertext()).split())
for spec in book['documents']:
 doc=spec['document_number'];src=registry.loc[spec['source_id']];meta=registry.loc[spec['metadata_source_id']]
 body=(ROOT/src.path).read_bytes();meta_body=(ROOT/meta.path).read_bytes();root=ET.fromstring(body);metadata=json.loads(meta_body)
 source_hashes[doc]=dict(xml_sha256=hashlib.sha256(body).hexdigest(),metadata_sha256=hashlib.sha256(meta_body).hexdigest())
 check(doc+':raw_snapshots',source_hashes[doc]['xml_sha256']==spec['source_sha256']==src.sha256 and source_hashes[doc]['metadata_sha256']==spec['metadata_sha256']==meta.sha256)
 check(doc+':native_metadata_identity_dates',metadata['document_number']==doc and metadata['publication_date']==spec['publication_date'] and metadata['effective_on']==spec['effective_date'])
 trailer=norm(root.find('FRDOC'));m=re.search(r'Filed\s+(\d{1,2})-(\d{1,2})-(\d{2,4})',trailer)
 year=int(m[3]);year=year+2000 if year<100 else year
 filed=date(year,int(m[1]),int(m[2])).isoformat();effective=spec['effective_date'];published=metadata['publication_date']
 native[doc]=dict(root=root,filed=filed,published=published,effective=effective)
 check(doc+':native_effective_sentence',norm(root.find('./PREAMB/EFFDATE/P'))=='This rule is effective '+datetime.strptime(effective,'%Y-%m-%d').strftime('%B %d, %Y').replace(' 0',' ')+'.')
 row=clocks[clocks.document_number.eq(doc)].iloc[0]
 check(doc+':three_clocks',row.info_public_date==filed and row.publication_date==published and row.effective_date==effective)
 check(doc+':notice_days',row.reported_filing_lead_days==(date.fromisoformat(effective)-date.fromisoformat(filed)).days and row.publication_lead_days==(date.fromisoformat(effective)-date.fromisoformat(published)).days)
 for claim in spec['claims']:
  exact=norm(root.find(claim['xpath']));row=clauses[clauses.claim_id.eq(claim['claim_id'])]
  check(claim['claim_id']+':native_xpath_quote',len(row)==1 and exact==claim['quote']==row.iloc[0]['quote'])
  if claim['source_role'].startswith('operative_'):check(claim['claim_id']+':operative_text_role','/REGTEXT[' in claim['xpath'])
  if claim['source_role'].startswith('explanatory_'):check(claim['claim_id']+':explanatory_not_operative','/REGTEXT[' not in claim['xpath'] and row.iloc[0].source_role=='explanatory_preamble_not_complete_rule')
root=native['2023-22873']['root'];tables=root.findall('.//GPOTABLE');check('permission:one_native_table',len(tables)==1)
rows=[r for r in tables[0].findall('ROW') if len(r.findall('ENT'))==4]
check('permission:entire_printed_recipient_set',len(rows)==2)
for i,row in enumerate(rows):
 cells=[norm(x) for x in row.findall('ENT')];expected=events[events.event_kind.eq('permission_scope_amendment') & events.party_name.eq(cells[0])]
 check('permission:'+str(i)+':exact_four_cells',len(expected)==1 and all(expected.iloc[0][key]==value for key,value in zip(['party_name','eligible_items','eligible_destination','native_citation'],cells)))
 for token in ['except','EUV','parts','components','software','technology','development','production','744.6(c)(2)(i-iii)','744.23(a)(1)(iii)','(a)(2)(iii)','748.15(d)']:
  check('permission:'+str(i)+':exception_or_conjunction:'+token,token in cells[1])
 check('permission:'+str(i)+':uncorrected_citation_placeholder','[INSERT PAGE NUMBER]' in cells[3])
check('permission:NAND_and_DRAM_facilities_bound',any('NAND memory' in norm(r) and 'No. 1999, North Xiaohe Road' in norm(r) for r in rows) and any('dynamic random-access memory (DRAM)' in norm(r) and 'Lot K7, Wuxi High-tech Zone' in norm(r) for r in rows))
q=clauses[clauses.claim_id.eq('VEU:2023-22873:INSTRUCTION')].iloc[0]['quote'];check('permission:explicit_country_amendatory_context',"China (People's Republic of)" in q)
q=clauses[clauses.claim_id.eq('VEU:2023-22873:SECTION_INSTRUCTION')].iloc[0]['quote'];check('permission:partial_paragraph_adding_sentence_not_all_new', 'adding a sentence after the first sentence' in q and '§ 748.15(d)' in q)
q=clauses[clauses.claim_id.eq('VEU:2023-22873:NONSUPERSESSION')].iloc[0]['quote'];check('permission:other_EAR_qualifier_preserved','Nothing in this Supplement shall be deemed to supersede other provisions in the EAR' in q and '748.15(c)' in q)
removal=clauses[clauses.claim_id.eq('VEU:2025-16735:REMOVAL')].iloc[0]['quote'];names=re.findall('“([^”]+)”',removal)
check('removal:three_explicit_recipients_and_country',names==['Intel Semiconductor (Dalian) Ltd','Samsung China Semiconductor Co. Ltd','SK hynix Semiconductor (China) Ltd',"China (People's Republic of)"])
removed=events[events.event_kind.eq('authorization_removal')]
check('removal:three_events_not_prohibitions',len(removed)==3 and removed.permission_type.eq('removes_selected_general_authorization_not_an_export_prohibition').all())
check('removal:unknown_prior_Intel_scope_stays_missing',len(removed[removed.party_id.eq('intel_dalian')])==1 and removed[removed.party_id.eq('intel_dalian')][['eligible_items','eligible_destination','memory_scope']].eq('').all().all())
check('links:only_two_named_recipient_document_pairs',len(links)==2 and not links.continuous_authorization_between_sources_certified.any() and not links.actual_technology_access_certified.any())
for _,row in origins.iterrows():
 origin=row.origin;visible=[x for x in events.to_dict('records') if x['info_public_date']<=origin];alt=[x for x in events.to_dict('records') if x['publication_date']<=origin]
 future=sum(x['effective_date']>origin for x in visible)
 check('origin:'+origin+':independent_date_ordering',row.visible_issued_events==len(visible) and row.publication_only_events==len(alt) and row.known_future_effective_events==future and row.issued_effective_date_reached==len(visible)-future and not row.active_authorization_set_certified)
check('origin:2025_08_29_removals_are_future',origins[origins.origin.eq('2025-08-29')].iloc[0].known_future_effective_events==3)
check('origin:post_effective_records_are_history_not_active_set',origins[origins.origin.eq('2025-12-31')].iloc[0].visible_issued_events==5 and origins[origins.origin.eq('2025-12-31')].iloc[0].known_future_effective_events==0)
for field in ['domestic_capability_score','foreign_access_score','observed_license_outcome']:
 check('scientific_labels:'+field+':no_fabricated_values',events[field].eq('').all())
for field in ['complete_legal_eligibility_certified','current_law_consolidation_verified','source_byte_vintage_independently_certified']:
 check('scientific_labels:'+field+':no_stronger_certificate',not events[field].any())
report=dict(review_harness_corrections='Initial review used two nonliteral wording shortcuts (paragraph(d), does not supersede); corrected to the actual §748.15(d) and Nothing ... shall be deemed wording, without changing source claims or VEU implementation. Initial diagnostic preserved separately.',passed=not failures,execution_timestamp=datetime.now(timezone.utc).isoformat(),reviewer='internal_independent_computational_agent',
 scope='Independent XML/metadata/CSV checks using ElementTree, literal token and date comparisons; no calls to the VEU extraction or query implementation',
 checks=len(checks),failures=failures,checks_detail=checks,original_snapshot_hashes=source_hashes,
 primary_claims_rechecked=18,permission_entries_rechecked=2,removal_recipients_rechecked=3,origin_phase_checks_rechecked=len(origins),
 external_legal_review=False,independent_human_coding=False,second_machine_replication=False,
 current_law_consolidation_certified=False,transaction_eligibility_certified=False,actual_technology_access_estimated=False,
 historical_original_bytes_certified=False,
 residual_requirements=['Complete intervening EAR provisions/amendments and other authorizations','Transaction-specific licensing and shipment/servicing evidence','Qualified independent legal interpretation','Globally earliest disclosure and release-time original-byte corroboration'])
(ROOT/'outputs/diagnostics/veu_independent_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks_detail','original_snapshot_hashes']},indent=2))
if failures:raise SystemExit(1)
