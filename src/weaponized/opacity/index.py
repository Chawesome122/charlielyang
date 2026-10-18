"""Daily and quarterly SPOI with immutable pillar weights and coverage gates."""
import math
import pandas as pd
from .coding import CODES, PILLARS, WEIGHTS
from .events import event_score, date, known_rows, is_covered
from .obligations import obligation_score, DISCLOSURE


def aggregate_scores(scores, min_daily_indicators=8, weights=None):
    weights = WEIGHTS if weights is None else weights
    if set(weights) != set(PILLARS) or any(v < 0 for v in weights.values()) or not math.isclose(sum(weights.values()), 1):
        raise ValueError('weights must be nonnegative, cover every pillar, and sum to one')
    observed = {k: float(v) for k,v in scores.items() if k in CODES and v is not None and not pd.isna(v)}
    if any(not math.isfinite(v) or not 0 <= v <= 4 for v in observed.values()):
        raise ValueError('ordinal scores must be finite and within [0,4]')
    counts = {p: sum(k in observed for k in keys) for p,keys in PILLARS.items()}
    valid = len(observed) >= min_daily_indicators and counts['disclosure'] >= 3 and counts['predictability'] >= 2 and counts['clarity'] >= 1
    out = {'observed_indicators': len(observed), 'daily_valid': valid}
    for p, keys in PILLARS.items():
        out[p + '_count'] = counts[p]
        out[p] = sum(observed[k] for k in keys if k in observed)/(4*counts[p]) if counts[p] else float('nan')
    out['spoi'] = 100*sum(weights[p]*out[p] for p in PILLARS) if valid else float('nan')
    return out


def spoi_daily(obligations, legal_events, source_events, codebook, start, end):
    """Return ten explicit codes, status/reason, denominators, and validity.

    Evidence is only visible at info_public_date; actual-date observations do not
    silently become known earlier. `source_events` carries dated, adjudicated search
    coverage; an empty research database does not establish a zero-event universe.
    """
    settings = codebook or {}
    if not isinstance(settings, dict):
        raise TypeError('codebook must contain locked settings as a mapping')
    start, end = date(start), date(end)
    if start > end:
        raise ValueError('start follows end')
    rows = []
    for stamp in pd.date_range(start, end, freq='D'):
        day = stamp.date()
        row = {'date': day.isoformat()}
        for indicator in CODES:
            if indicator in DISCLOSURE:
                obs = obligation_score(indicator, obligations, day, settings.get('release_grace_days', 30))
            else:
                obs = event_score(indicator, legal_events, source_events, day,
                                  settings.get('event_memory_days', 90), settings.get('legal_rule_aggregation', 'worst'))
            row[indicator] = obs.score
            row[indicator + '_status'] = obs.status
            row[indicator + '_reason'] = obs.reason
            row[indicator + '_numerator'] = obs.numerator
            row[indicator + '_denominator'] = obs.denominator
        row.update(aggregate_scores(row, settings.get('min_daily_indicators', 8), settings.get('pillars')))
        event_count = len({r.get('intervention_id') or r.get('event_id') for r in known_rows(legal_events, day)
                           if date(r.get('publication_date')) == day and r.get('event_type') not in {'legal_rule', 'conflict'}})
        row['legal_events_recorded'] = event_count
        row['legal_events'] = event_count if all(is_covered(source_events, k, day) for k in ('O4','O6','O10')) else float('nan')
        rows.append(row)
    return pd.DataFrame(rows)


def quarterly_spoi(daily, min_valid_fraction=.80):
    """Use every calendar day as denominator, including days absent from input."""
    if not 0 <= min_valid_fraction <= 1:
        raise ValueError('coverage fraction outside [0,1]')
    frame = daily.copy()
    frame['date'] = pd.to_datetime(frame['date'])
    if frame['date'].duplicated().any():
        raise ValueError('duplicate calendar days')
    frame['quarter'] = frame['date'].dt.to_period('Q')
    rows = []
    for q, sub in frame.groupby('quarter'):
        total_days = (q.end_time.date() - q.start_time.date()).days + 1
        valid = sub['daily_valid'].fillna(False).astype(bool) & sub['spoi'].notna()
        nvalid = int(valid.sum())
        coverage = nvalid / total_days
        result = {'quarter': str(q), 'calendar_days': total_days, 'recorded_days': len(sub),
                  'valid_days': nvalid, 'coverage': coverage, 'quarter_valid': coverage >= min_valid_fraction,
                  'spoi': float(sub.loc[valid, 'spoi'].mean()) if coverage >= min_valid_fraction else float('nan'),
                  'quarter_max': float(sub.loc[valid, 'spoi'].max()) if coverage >= min_valid_fraction else float('nan'),
                  'legal_events': sub.get('legal_events', pd.Series(dtype=float)).sum(min_count=1)}
        for indicator in CODES:
            result[indicator + '_observed_days'] = int(sub[indicator].notna().sum())
        rows.append(result)
    return pd.DataFrame(rows)


def opacity_regression_gate(quarterly, project_panel=None):
    """No regression is emitted when the regressor or project risk set is absent."""
    usable = quarterly.loc[quarterly['quarter_valid'] & quarterly['spoi'].notna()]
    reasons = []
    if usable.empty:
        reasons.append('no_coverage_valid_quarterly_SPOI')
    if project_panel is None or len(project_panel) == 0:
        reasons.append('no_linked_project_transition_risk_set_and_support_uncertainty_controls')
    required = {'project_id', 'quarter', 'transition', 'government_support', 'technology_uncertainty', 'market_uncertainty'}
    if project_panel is not None and len(project_panel) and not required.issubset(project_panel.columns):
        reasons.append('project_panel_missing_prespecified_controls_or_transition_fields')
    if not usable.empty and usable['spoi'].nunique() < 3:
        reasons.append('insufficient_opacity_support_for_linear_and_quadratic_terms')
    # Passing this gate is eligibility for design review, not a causal identification claim.
    return {'status': 'BLOCKED' if reasons else 'DESIGN_REVIEW_REQUIRED', 'reasons': reasons,
            'eligible_quarters': len(usable), 'causal_identification': 'not_established'}
