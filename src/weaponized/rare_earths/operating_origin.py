"""Source-vintaged ownership, commercial routing and procurement admission checks.

A known non-China location never certifies full-route China independence.
These helpers do not solve a material network or infer missing physical volumes.
"""
from datetime import date
from calendar import monthrange
from pathlib import Path
import re

from weaponized.io.original_text import normalize_evidence, verified_original_text


def original_claim(spec, sources, public_dates, root):
    """Bind one quote and value to its immutable original, source and date."""
    source = sources[spec['source_id']]
    if source['sha256'] != spec['source_sha256']:
        raise ValueError('Claim original digest differs from source registry')
    public = source.get('publication_date')
    if not public or public != public_dates[spec['source_id']] or public > '2026-10-11':
        raise ValueError('Missing, changed or post-freeze original public clock')
    text = normalize_evidence(verified_original_text(Path(root)/source['archive_path'], spec['source_sha256']))
    quote = normalize_evidence(spec['quote'])
    if not quote:
        raise ValueError('Empty evidence cannot support an operating-origin claim')
    matches = list(re.finditer(re.escape(quote), text))
    ordinal = spec['match_ordinal']
    if len(matches) != spec['expected_quote_matches'] or not 0 <= ordinal < len(matches):
        raise ValueError('Original quote or expected occurrence count changed')
    if spec.get('value_pattern'):
        match = re.search(spec['value_pattern'], quote)
        if not match or float(match['value']) != spec['value']:
            raise ValueError('Claim numerical value lacks its named source binding')
    elif str(spec['value']) not in quote:
        raise ValueError('Claim categorical value absent from original quote')
    low, high = spec.get('event_date_lower'), spec.get('event_date_upper')
    if bool(low) != bool(high) or (low and (date.fromisoformat(low) > date.fromisoformat(high) or spec['valid_date'] != high)):
        raise ValueError('Invalid event interval or misleading indexing date')
    if date.fromisoformat(spec['valid_date']) > date.fromisoformat(public):
        raise ValueError('Observed reporting/event index cannot follow selected publication')
    if low:
        months = 'January February March April May June July August September October November December'.split()
        allowed = set()
        for month, year in re.findall(r'\b(?:In|in) ('+'|'.join(months)+r') (\d{4})\b', quote):
            y, m = int(year), months.index(month)+1
            allowed.add((date(y,m,1).isoformat(),date(y,m,monthrange(y,m)[1]).isoformat()))
        for quarter, year in re.findall(r'\b(first|second|third|fourth) quarter of (\d{4})\b', quote):
            y, q = int(year), ['first','second','third','fourth'].index(quarter)+1
            start, end = 3*q-2, 3*q
            allowed.add((date(y,start,1).isoformat(),date(y,end,monthrange(y,end)[1]).isoformat()))
        if (low,high) not in allowed or high > public:
            raise ValueError('Event interval lacks an explicit source month/quarter/year or follows publication')
    if spec['variable']=='reported_reagent_and_material_purchases':
        years = [int(x) for x in re.findall(r'\b20\d{2}\b',quote.split('$',1)[0])]
        amounts = [float(x) for x in re.findall(r'\$\s*(\d+(?:\.\d+)?) million',quote)]
        year = date.fromisoformat(spec['reporting_period_end']).year
        if len(years)!=3 or len(amounts)!=3 or year not in years or amounts[years.index(year)]!=spec['value']:
            raise ValueError('Financial value is not bound to its reported year')
        if spec['native_unit']!='USD million' or spec['valid_date']!=spec['reporting_period_end']:
            raise ValueError('Financial unit/period cannot be substituted for physical supply')
    elif spec['reporting_period_end'] != spec['source_id'][-4:]+'-12-31':
        raise ValueError('Report-snapshot index differs from its registered annual source')
    return dict(quote=quote, source=source, normalized_original_start=matches[ordinal].start(),
                normalized_original_end=matches[ordinal].end(), quote_matches=len(matches))


def visible_claims(claims, origin):
    """Archive-public information set; not a certificate of current ownership."""
    origin = date.fromisoformat(str(origin))
    return [row for row in claims if date.fromisoformat(row['info_public_date']) <= origin]


def route_evidence_admission(processing_country, group_link_reported, *, group_excluded=False,
                             all_input_origins_verified=None, finite_volume_verified=None,
                             qualification_verified=None, ownership_at_origin_verified=None,
                             material_recipe_and_recovery_verified=None,
                             route_rights_and_throughput_verified=None,grade_demand_verified=None):
    """Separate location, supplier-group exclusion and full-route data readiness.

    `group_link_reported` is case-specific source evidence, not a determination
    of national legal control. Unknown booleans remain unknown, never False=zero.
    """
    if group_link_reported is not None and type(group_link_reported) is not bool:
        raise ValueError('Group-link evidence must be true, false or missing')
    flags = dict(all_input_origins_verified=all_input_origins_verified,
                 finite_volume_verified=finite_volume_verified,
                 qualification_verified=qualification_verified,
                 ownership_at_origin_verified=ownership_at_origin_verified,
                 material_recipe_and_recovery_verified=material_recipe_and_recovery_verified,
                 route_rights_and_throughput_verified=route_rights_and_throughput_verified,grade_demand_verified=grade_demand_verified)
    if type(group_excluded) is not bool or any(value is not None and type(value) is not bool for value in flags.values()):
        raise ValueError('Admission fields must be true, false or missing')
    aliases = {
        'china':'China','cn':'China','chn':'China','prc':'China',
        "people's republic of china":'China',"china (people's republic of)":'China',
        'vietnam':'Vietnam','vn':'Vietnam','vnm':'Vietnam',
        'united states':'United States','united states of america':'United States',
        'us':'United States','usa':'United States','u.s.':'United States','u.s.a.':'United States',
    }
    if processing_country is not None and not isinstance(processing_country,str):
        raise ValueError('Processing country must be a reviewed country string or missing')
    normalized = ' '.join((processing_country or '').casefold().split())
    if normalized and normalized not in aliases:
        raise ValueError('Unreviewed processing-country label; register source-supported representation first')
    processing_country = aliases.get(normalized)
    if processing_country == 'China':
        location = 'excluded_by_reported_processing_location'
    elif processing_country:
        location = 'not_excluded_by_reported_location_alone'
    else:
        location = 'processing_location_unresolved'
    group = ('excluded_by_registered_supplier_group_sensitivity' if group_excluded and group_link_reported is True
             else 'supplier_group_link_unresolved' if group_excluded and group_link_reported is None
             else 'not_excluded_by_registered_supplier_group_sensitivity')
    missing = [name for name, value in flags.items() if value is None]
    failed = [name for name, value in flags.items() if value is False]
    admitted = location == 'not_excluded_by_reported_location_alone' and not missing and not failed and not group.startswith('excluded') and not (group_excluded and group_link_reported is None)
    return dict(location_screen=location, supplier_group_screen=group, missing_requirements=missing,
                failed_requirements=failed, full_route_data_admitted=admitted,
                empirical_delivered_service=None, empirical_delivered_service_missing_reason='No complete element/grade/rate/material/demand network is supplied by this evidence screen')
