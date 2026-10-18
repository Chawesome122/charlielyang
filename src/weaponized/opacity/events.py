"""Publication-clock-aware policy-event stocks and rolling windows."""
from datetime import timedelta
import pandas as pd
from .coding import CodedObservation, unavailable, score_lead_time, score_churn, score_legal_scope, score_conflicts


def date(value):
    if value is None or pd.isna(value) or value == '':
        return None
    return pd.Timestamp(value).date()


def truth(value):
    return value is True or str(value).lower() in {'true', '1', 'yes'}


def known_rows(frame, day):
    if frame is None or len(frame) == 0:
        return []
    rows = frame.to_dict('records') if hasattr(frame, 'to_dict') else frame
    known = [r for r in rows if date(r.get('info_public_date')) is not None and date(r['info_public_date']) <= day]
    # Keep superseded observations immutable, selecting only the last public version
    # for the same record at this vintage. Distinct events retain distinct keys.
    keyed, unkeyed = {}, []
    for row in known:
        key = next(((field, row[field]) for field in ('obligation_id', 'event_id', 'coverage_id', 'observation_id')
                    if row.get(field) is not None and not pd.isna(row.get(field))), None)
        if key is None:
            unkeyed.append(row)
        else:
            order = (date(row['info_public_date']), str(row.get('record_version_id', '')))
            if key not in keyed or order > keyed[key][0]:
                keyed[key] = (order, row)
    return unkeyed + [item[1] for item in keyed.values()]


def is_covered(source_events, indicator, day):
    for row in known_rows(source_events, day):
        if row.get('kind') == 'coverage' and row.get('indicator') in {indicator, 'ALL'}:
            lo, hi = date(row.get('valid_from')), date(row.get('valid_until'))
            if lo and hi and lo <= day <= hi and truth(row.get('adjudicated')):
                return True
    return False


def event_score(indicator, legal_events, source_events, day, memory_days=90, legal_aggregation='worst'):
    if not is_covered(source_events, indicator, day):
        return unavailable('policy_event_universe_or_search_coverage_not_adjudicated')
    rows = known_rows(legal_events, day)
    public_rows = [r for r in rows if date(r.get('publication_date')) and date(r['publication_date']) <= day]
    lower = day - timedelta(days=memory_days)
    if indicator == 'O4':
        events = [r for r in public_rows if r.get('event_type') == 'new_policy' and truth(r.get('substantive', True))
                  and lower < date(r['publication_date']) <= day
                  and (date(r.get('end_date')) is None or day < date(r['end_date']))]
        if any(date(r.get('effective_date')) is None for r in events):
            return unavailable('qualifying_policy_has_unknown_effective_date')
        values = [score_lead_time((date(r['effective_date']) - date(r['publication_date'])).days) for r in events]
        return CodedObservation(max(values, default=0), 'observed', 'worst_recent_policy_lead_time' if events else 'no_recent_policy_lead_time_event', len(events), None)
    if indicator == 'O6':
        events = [r for r in public_rows if r.get('event_type') == 'adverse_reversal' and truth(r.get('material'))]
        active = []
        for row in events:
            effective, pub = date(row.get('effective_date')), date(row['publication_date'])
            if effective is None:
                if pub > lower:
                    return unavailable('qualifying_reversal_has_unknown_effective_date')
                continue
            # Observe from announcement, retaining 90 days after the later clock.
            if day < max(pub, effective) + timedelta(days=memory_days):
                active.append(row)
        values = [score_lead_time((date(r['effective_date']) - date(r['publication_date'])).days) for r in active]
        return CodedObservation(max(values, default=0), 'observed', 'worst_public_adverse_reversal' if active else 'no_qualifying_adverse_reversal', len(active), None)
    if indicator == 'O10':
        events = [r for r in public_rows if r.get('event_type') == 'amendment' and truth(r.get('material'))]
        ids = set()
        for row in events:
            effective = date(row.get('effective_date'))
            if effective is None:
                if date(row['publication_date']) > lower:
                    return unavailable('material_amendment_has_unknown_effective_date')
                continue
            clock = max(date(row['publication_date']), effective)
            if lower < clock <= day:
                ids.add(row.get('intervention_id') or row['event_id'])
        return CodedObservation(score_churn(len(ids)), 'observed', 'deduplicated_public_effective_amendments', len(ids), None)
    if indicator == 'O5':
        rules = [r for r in public_rows if r.get('event_type') == 'legal_rule' and date(r.get('effective_date'))
                 and date(r['effective_date']) <= day and (date(r.get('end_date')) is None or day < date(r['end_date']))]
        if not rules:
            return unavailable('adjudicated_universe_has_no_current_effective_rule', 'not_applicable')
        if any(pd.isna(r.get('explicit_scope_fields')) for r in rules):
            return unavailable('scope_fields_not_independently_coded')
        scores = [score_legal_scope(int(r['explicit_scope_fields'])) for r in rules]
        if legal_aggregation == 'worst':
            value = max(scores)
        elif legal_aggregation == 'exposure_weighted':
            weights = [r.get('frozen_exposure_weight') for r in rules]
            if any(w is None or pd.isna(w) or w < 0 for w in weights) or sum(weights) <= 0:
                raise ValueError('positive frozen pre-exposure weights required')
            if any(date(r.get('weight_info_public_date')) is None or date(r['weight_info_public_date']) > date(r['publication_date']) for r in rules):
                raise ValueError('exposure weights cannot postdate the policy')
            value = sum(s*w for s,w in zip(scores,weights))/sum(weights)
        else:
            raise ValueError('unknown prespecified legal aggregation')
        return CodedObservation(value, 'observed', 'current_rules_' + legal_aggregation, len(rules), 4*len(rules))
    if indicator == 'O7':
        conflicts = []
        for row in public_rows:
            if row.get('event_type') != 'conflict':
                continue
            resolution = date(row.get('resolution_date'))
            resolution_public = date(row.get('resolution_info_public_date'))
            # A retrospectively observed resolution cannot silently shorten the
            # historical stock before the public resolution evidence was available.
            if resolution is None or resolution_public is None or resolution_public > day or day < resolution + timedelta(days=memory_days):
                conflicts.append(row)
        if any(r.get('materiality') not in {'minor', 'material'} for r in conflicts):
            return unavailable('conflict_materiality_not_adjudicated')
        nminor = sum(r['materiality'] == 'minor' for r in conflicts)
        nmaterial = sum(r['materiality'] == 'material' for r in conflicts)
        return CodedObservation(score_conflicts(nminor, nmaterial, any(truth(r.get('material_no_resolution')) for r in conflicts)), 'observed', 'conflicts_plus_post_resolution_window', nminor+nmaterial, None)
    raise ValueError('unsupported event indicator')
