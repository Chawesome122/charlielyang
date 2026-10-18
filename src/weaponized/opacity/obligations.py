"""Dated release obligations with separately dated evidence of release/absence."""
from datetime import timedelta
import pandas as pd
from .coding import (CodedObservation, unavailable, score_lateness, score_missing_fields,
                     score_availability, score_absent_releases)
from .events import date, known_rows, truth

DISCLOSURE = {'O1', 'O2', 'O3', 'O8', 'O9'}


def obligation_score(indicator, obligations, day, grace_days=30):
    if indicator not in DISCLOSURE:
        raise ValueError('not a disclosure indicator')
    rows = [r for r in known_rows(obligations, day) if indicator in str(r.get('indicators', '')).split(';')]
    if not rows:
        return unavailable('objective_obligation_or_frozen_denominator_not_established', 'not_applicable')
    if any(not r.get('denominator_source_id') or pd.isna(r.get('denominator_source_id')) for r in rows):
        return unavailable('expected_denominator_source_not_registered')
    if indicator == 'O8':
        eligible = [r for r in rows if date(r.get('due_date')) and day-timedelta(days=365) < date(r['due_date']) + timedelta(days=grace_days) <= day]
    else:
        eligible = [r for r in rows if date(r.get('due_date')) and date(r['due_date']) <= day
                    and date(r.get('observation_end_date')) and day < date(r['observation_end_date'])]
    if not eligible:
        return unavailable('no_obligation_in_current_observation_window', 'not_applicable')
    # The researcher's inability to retrieve a release is not proof of its absence.
    def release_known(row):
        pub = date(row.get('release_info_public_date'))
        return pub is not None and pub <= day and date(row.get('release_date')) is not None
    def absence_known(row):
        checked = date(row.get('absence_verified_on'))
        return truth(row.get('affirmatively_absent')) and checked is not None and checked <= day
    if indicator == 'O1':
        values = []
        for row in eligible:
            due = date(row['due_date'])
            if release_known(row):
                lag = max(0, (date(row['release_date']) - due).days)
            elif absence_known(row):
                lag = max(0, (day - due).days)
            else:
                return unavailable('release_or_absence_not_verified')
            nxt = date(row.get('next_due_date'))
            values.append(score_lateness(lag, nxt is not None and day >= nxt and not release_known(row)))
        return CodedObservation(max(values), 'observed', 'worst_active_known_release_lateness', max(values), len(values))
    if indicator == 'O8':
        missing = 0
        for row in eligible:
            checkpoint = date(row['due_date'])+timedelta(days=grace_days)
            if release_known(row):
                missing += date(row['release_date']) > checkpoint
            elif absence_known(row):
                missing += 1
            else:
                return unavailable('rolling_release_checkpoint_not_adjudicated')
        return CodedObservation(score_absent_releases(missing/len(eligible)), 'observed', 'rolling_365_day_absence_at_due_plus_grace', missing, len(eligible))
    metrics = {'O2': ('missing_required_fields', 'required_fields', score_missing_fields),
               'O3': ('available_license_metrics', 'expected_license_metrics', score_availability),
               'O9': ('classifiable_throughput', 'total_documented_throughput', score_availability)}
    numfield, denfield, scorer = metrics[indicator]
    if any(not release_known(r) for r in eligible):
        return unavailable('scheduled_release_metrics_not_observed')
    if any(r.get(numfield) is None or pd.isna(r.get(numfield)) or r.get(denfield) is None or pd.isna(r.get(denfield)) for r in eligible):
        return unavailable('required_field_or_metric_denominator_not_observed')
    if indicator == 'O9':
        units = {r.get('measurement_unit') for r in eligible}
        bases = {r.get('measurement_basis') for r in eligible}
        if None in units or None in bases or any(pd.isna(x) for x in units | bases) or len(units) != 1 or len(bases) != 1:
            return unavailable('O9_reported_quantities_require_one_documented_comparable_unit_and_basis')
    numerator = sum(float(r[numfield]) for r in eligible)
    denominator = sum(float(r[denfield]) for r in eligible)
    if denominator <= 0:
        return unavailable('no_expected_items_in_registered_denominator', 'not_applicable')
    return CodedObservation(scorer(numerator/denominator), 'observed', 'documented_current_release_fraction', numerator, denominator)
