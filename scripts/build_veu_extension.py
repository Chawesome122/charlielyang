"""Rebuild selected facility/item VEU permissions and later issued removals."""
from datetime import date
import hashlib
import json
from pathlib import Path

import pandas as pd

from weaponized.semiconductors.veu_extension import (
    verify_original, permission_rows, removal_rows, issued_veu_events,
)

ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT):
    book = json.loads((root/'codebooks/veu_extension.json').read_text())
    sources = pd.read_csv(root/'metadata/semiconductor_sources.csv').fillna('').set_index('source_id')
    claims, events, clocks = [], [], []
    for spec in book['documents']:
        source = sources.loc[spec['source_id']]
        meta = sources.loc[spec['metadata_source_id']]
        if source.sha256 != spec['source_sha256'] or meta.sha256 != spec['metadata_sha256']:
            raise ValueError('VEU source registry differs from pinned original snapshots')
        payload = (root/source.path).read_bytes()
        metadata_payload = (root/meta.path).read_bytes()
        parsed, exact_claims, clock = verify_original(payload, metadata_payload, spec, book['freeze'])
        common = dict(source_id=spec['source_id'], source_sha256=spec['source_sha256'], source_path=source.path,
                      source_url=source.url, retrieval_timestamp=source.retrieval_timestamp,
                      metadata_source_id=spec['metadata_source_id'], metadata_sha256=spec['metadata_sha256'],
                      document_number=spec['document_number'], original_citation=spec['original_citation'], **clock,
                      source_byte_vintage_independently_certified=False,
                      first_public_clock_basis='Original FRDOC reported filing dateline; end-of-day convention; globally earliest disclosure not certified')
        claims.extend(dict(common, **claim) for claim in exact_claims)
        clocks.append(dict(common, publication_lead_days=(date.fromisoformat(clock['effective_date'])-date.fromisoformat(clock['publication_date'])).days,
                           reported_filing_lead_days=(date.fromisoformat(clock['effective_date'])-date.fromisoformat(clock['info_public_date'])).days))
        if spec['document_number'] == '2023-22873':
            for row in permission_rows(parsed, spec):
                party = next(p for p in book['parties'] if p['party_id'] == row['party_id'])
                events.append(dict(common, **row, event_id='VEU:2023-22873:'+row['party_id'],
                                   event_kind='permission_scope_amendment', memory_scope=party['memory_scope'],
                                   source_claim_id='VEU:2023-22873:'+row['party_id'].upper()+':ELIGIBLE_ITEMS',
                                   permission_type='conditional_general_authorization_for_printed_items_and_facility',
                                   complete_legal_eligibility_certified=False, current_law_consolidation_verified=False,
                                   domestic_capability_score=None, foreign_access_score=None,
                                   observed_license_outcome=None))
        else:
            for row in removal_rows(parsed, spec, book['parties']):
                events.append(dict(common, **row, event_id='VEU:2025-16735:'+row['party_id'],
                                   event_kind='authorization_removal', source_claim_id=row['claim_id'],
                                   permission_type='removes_selected_general_authorization_not_an_export_prohibition',
                                   eligible_items=None, eligible_destination=None, memory_scope=None,
                                   complete_legal_eligibility_certified=False, current_law_consolidation_verified=False,
                                   domestic_capability_score=None, foreign_access_score=None,
                                   observed_license_outcome=None))
    if len(claims) != 18 or len(events) != 5 or len(clocks) != 2:
        raise ValueError('Unexpected selected VEU source/extraction counts')
    links = []
    for party in book['parties']:
        prior = [e for e in events if e['party_id'] == party['party_id'] and e['event_kind'] == 'permission_scope_amendment']
        removed = next(e for e in events if e['party_id'] == party['party_id'] and e['event_kind'] == 'authorization_removal')
        if not prior:
            continue
        if len(prior) != 1 or prior[0]['party_name'] != removed['party_name']:
            raise ValueError('VEU explicit named-recipient link differs from source')
        links.append(dict(party_id=party['party_id'], permission_event_id=prior[0]['event_id'],
                          removal_event_id=removed['event_id'], permission_source_sha256=prior[0]['source_sha256'],
                          removal_source_sha256=removed['source_sha256'],
                          permission_effective_date=prior[0]['effective_date'], removal_effective_date=removed['effective_date'],
                          link_basis='Exact source-native named recipient; selected original document pair, not complete amendment continuity',
                          continuous_authorization_between_sources_certified=False, actual_technology_access_certified=False))
    checks = []
    for origin in ['2023-10-12','2023-10-13','2023-10-16','2023-10-17',
                   '2025-08-28','2025-08-29','2025-09-01','2025-09-02','2025-12-30','2025-12-31',book['freeze']]:
        visible = issued_veu_events(events, origin)
        alternative = issued_veu_events(events, origin, 'publication')
        expected = [e for e in events if e['info_public_date'] <= origin]
        if len(visible) != len(expected) or any(e['current_authorization_certified'] or e['foreign_access_score'] is not None for e in visible):
            raise ValueError('VEU origin visibility or scientific-label check failed')
        checks.append(dict(origin=origin, visible_issued_events=len(visible), publication_only_events=len(alternative),
                           known_future_effective_events=sum(e['issued_phase']=='announced_not_effective' for e in visible),
                           issued_effective_date_reached=sum(e['issued_phase']!='announced_not_effective' for e in visible),
                           active_authorization_set_certified=False))
    out=root/'data/processed/veu_extension';out.mkdir(parents=True,exist_ok=True)
    datasets={'clauses':pd.DataFrame(claims),'issued_events':pd.DataFrame(events),
              'source_clocks':pd.DataFrame(clocks),'permission_removal_links':pd.DataFrame(links),
              'origin_phase_checks':pd.DataFrame(checks)}
    for name, frame in datasets.items():frame.to_csv(out/f'{name}.csv',index=False)
    result=dict(passed=True,freeze=book['freeze'],classification='primary_legal_descriptive_selected_issued_instruments',
                original_rules=2,source_snapshots=4,primary_quote_checks=18,rule_clock_checks=2,
                printed_permission_entries=2,explicit_removal_entries=3,link_checks=len(links),origin_phase_checks=len(checks),
                printed_permission_citation_placeholders=2,complete_legal_eligibility_certified=False,
                current_law_consolidation_verified=False,foreign_access_identified=False,domestic_capability_identified=False,
                actual_license_outcome_observed=False,causal_effect_identified=False,
                inherited_entity_footnote_closure_verified=False,
                unprinted_entity_footnote_blocker='Complete historical section/note versions and intervening amendments unavailable; two new official statutory-XML requests failed CONNECT 403',
                files={str((out/f'{name}.csv').relative_to(root)):hashlib.sha256((out/f'{name}.csv').read_bytes()).hexdigest() for name in datasets})
    diag=root/'outputs/diagnostics';diag.mkdir(parents=True,exist_ok=True)
    (diag/'veu_extension_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':build()
