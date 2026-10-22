"""Selected issued VEU permissions/removals; never actual access or current law."""
from datetime import date, datetime
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from .entity_schedules import reported_filing_date
from .legal import issued_xml_text
from .provisions import normalize_text, verify_clause


HEADERS = ['Country', 'Validated end-user', 'Eligible items (by ECCN)',
           'Eligible destination', 'Federal Register citation']


def verify_original(payload, metadata_payload, spec, freeze='2026-10-11'):
    """Check and parse the same immutable original snapshots used for claims."""
    for body, key in [(payload, 'source_sha256'), (metadata_payload, 'metadata_sha256')]:
        if hashlib.sha256(body).hexdigest() != spec[key]:
            raise ValueError('VEU original snapshot checksum mismatch')
    metadata = json.loads(metadata_payload)
    if metadata['document_number'] != spec['document_number']:
        raise ValueError('VEU metadata document identity mismatch')
    for key, native in [('publication_date', 'publication_date'), ('effective_date', 'effective_on')]:
        if metadata[native] != spec[key]:
            raise ValueError('VEU metadata date mismatch')
    if metadata['citation'] != spec['original_citation']:
        raise ValueError('VEU metadata citation mismatch')
    if date.fromisoformat(spec['publication_date']) > date.fromisoformat(freeze):
        raise ValueError('VEU source publication exceeds information freeze')
    issued_xml_text(payload, spec['document_number'])
    root = ET.fromstring(payload)
    if root.tag != 'RULE':
        raise ValueError('VEU source must be an issued original rule')
    effect = normalize_text(root.find('./PREAMB/EFFDATE/P'))
    if effect != 'This rule is effective ' + datetime.strptime(spec['effective_date'], '%Y-%m-%d').strftime('%B %d, %Y').replace(' 0', ' ') + '.':
        raise ValueError('VEU effective date lacks exact original support')
    trailer = normalize_text(root.find('./FRDOC'))
    public = reported_filing_date(trailer, spec['document_number'])
    if public > spec['publication_date']:
        raise ValueError('VEU reported filing follows publication')
    claims = []
    for claim in spec['claims']:
        quote = verify_clause(payload, spec['document_number'], claim['xpath'], claim['quote'])
        if claim['source_role'].startswith('operative_') and '/REGTEXT[' not in claim['xpath']:
            raise ValueError('VEU operative claim is not from amended legal text')
        claims.append(dict(claim, quote=quote))
    return root, claims, dict(info_public_date=public, reported_filing_quote=trailer,
                             effective_date=spec['effective_date'], publication_date=spec['publication_date'])


def permission_rows(root, spec):
    """Extract all original four-cell permission rows, preserving literal terms."""
    tables = root.findall('.//GPOTABLE')
    if len(tables) != 1 or tables[0].get('COLS') != '5':
        raise ValueError('VEU expected one reviewed five-column table')
    table = tables[0]
    if [normalize_text(x) for x in table.findall('./BOXHD/CHED')] != HEADERS:
        raise ValueError('VEU table column contract changed')
    result = []
    for ordinal, row in enumerate(table.findall('ROW'), 1):
        cells = row.findall('ENT')
        values = [normalize_text(c) for c in cells]
        if len(cells) == 4:
            result.append(dict(source_row_ordinal=ordinal,
                               **dict(zip(['party_name', 'eligible_items', 'eligible_destination', 'native_citation'], values))))
        elif len(cells) != 1 or (values[0].replace('*', '').strip() and not values[0].startswith('Nothing in this Supplement')):
            raise ValueError('Unreviewed substantive VEU table row')
    expected = {c['party_id']: c['quote'] for c in spec['claims'] if c.get('field') == 'party_name'}
    if len(result) != 2 or {r['party_name'] for r in result} != set(expected.values()):
        raise ValueError('VEU source recipient set differs from reviewed source')
    by_name = {v: k for k, v in expected.items()}
    for row in result:
        row['party_id'] = by_name[row['party_name']]
        for field in ['party_name', 'eligible_items', 'eligible_destination', 'native_citation']:
            claims = [c for c in spec['claims'] if c.get('party_id') == row['party_id'] and c.get('field') == field]
            if len(claims) != 1 or claims[0]['quote'] != row[field]:
                raise ValueError('VEU cell lacks exact reviewed source binding')
    return result


def removal_rows(root, spec, parties):
    """Read each explicitly named recipient, without manufacturing prior scope."""
    matches = [c for c in spec['claims'] if c['claim_id'].endswith(':REMOVAL')]
    if len(matches) != 1:
        raise ValueError('One explicit removal instruction is required')
    claim = matches[0]
    quote = normalize_text(root.find(claim['xpath']))
    if quote != claim['quote'] or not quote.startswith('2. Amend supplement no. 7 to part 748 by removing the entries'):
        raise ValueError('VEU removal instruction contract changed')
    names = re.findall('“([^”]+)”', quote)
    expected = [p['removal_party_name'] for p in parties]
    if len(names) != 4 or names[-1] != "China (People's Republic of)" or set(names[:-1]) != set(expected):
        raise ValueError('VEU removal recipient or destination set changed')
    return [dict(party_id=p['party_id'], party_name=p['removal_party_name'],
                 claim_id=claim['claim_id'], instruction_xpath=claim['xpath']) for p in parties]


def issued_veu_events(records, as_of, public_clock='reported_filing'):
    """Return visible issued events, including known future-effective removals.

    Earlier permission amendments remain historical records after removal. The
    result must never be interpreted as the currently authorized recipient set.
    """
    if public_clock not in {'reported_filing', 'publication'}:
        raise ValueError('Explicit reported_filing or publication clock required')
    origin = date.fromisoformat(as_of)
    key = 'info_public_date' if public_clock == 'reported_filing' else 'publication_date'
    output = []
    for row in records:
        if date.fromisoformat(row[key]) > origin:
            continue
        phase = ('announced_not_effective' if origin < date.fromisoformat(row['effective_date'])
                 else 'issued_effective_date_reached_not_current_law_certified')
        output.append(dict(row, issued_phase=phase, current_authorization_certified=False,
                           foreign_access_score=None, domestic_capability_score=None,
                           observed_license_outcome=None))
    return output
