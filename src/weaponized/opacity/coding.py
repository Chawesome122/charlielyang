"""Locked Section 7 ordinal rubrics; missingness is never an opacity score."""
from dataclasses import dataclass
import math

CODES = tuple(f'O{i}' for i in range(1, 11))
PILLARS = {'disclosure': ('O1', 'O2', 'O3', 'O8', 'O9'),
           'predictability': ('O4', 'O6', 'O10'), 'clarity': ('O5', 'O7')}
WEIGHTS = {'disclosure': .40, 'predictability': .35, 'clarity': .25}

@dataclass(frozen=True)
class CodedObservation:
    score: float | None
    status: str
    reason: str
    numerator: float | None = None
    denominator: float | None = None

    def __post_init__(self):
        if self.status not in {'observed', 'not_applicable', 'researcher_missing'}:
            raise ValueError('unrecognized missingness status')
        if self.status == 'observed':
            if self.score is None or not math.isfinite(self.score) or not 0 <= self.score <= 4:
                raise ValueError('observed score must be finite and within [0,4]')
        elif self.score is not None:
            raise ValueError('missing or NA observations cannot carry a numeric score')
        if self.status != 'observed' and not self.reason:
            raise ValueError('missingness requires a reason')


def unavailable(reason, status='researcher_missing'):
    return CodedObservation(None, status, reason)


def score_lateness(days, absent_next_cycle=False):
    if days < 0:
        raise ValueError('lateness cannot be negative')
    return 4 if absent_next_cycle or days > 180 else (0 if days == 0 else 1 if days <= 30 else 2 if days <= 90 else 3)


def score_lead_time(days):
    """Negative lead time is retroactive and scores 4."""
    return 0 if days >= 90 else 1 if days >= 60 else 2 if days >= 30 else 3 if days >= 7 else 4


def _fraction(value):
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('fraction must be finite and within [0,1]')
    return value


def score_missing_fields(fraction):
    value = _fraction(fraction)
    return 0 if value <= .05 else 1 if value <= .15 else 2 if value <= .30 else 3 if value <= .50 else 4


def score_availability(fraction):
    value = _fraction(fraction)
    return 0 if value >= .90 else 1 if value >= .70 else 2 if value >= .50 else 3 if value >= .25 else 4


def score_absent_releases(fraction):
    value = _fraction(fraction)
    return 0 if value == 0 else 1 if value <= .10 else 2 if value <= .25 else 3 if value <= .50 else 4


def score_legal_scope(explicit_fields):
    if explicit_fields not in range(5):
        raise ValueError('exactly four registered legal scope fields')
    return 4 - explicit_fields


def score_conflicts(minor, material, material_no_resolution=False):
    if int(minor) != minor or int(material) != material or min(minor, material) < 0:
        raise ValueError('conflict counts must be nonnegative integers')
    # The codebook phrase 'material no resolution' needs explicit evidence/adjudication;
    # it is not inferred merely because a material conflict is still open today.
    if material_no_resolution or material >= 3:
        return 4
    if material == 2:
        return 3
    if material == 1 or minor >= 2:
        return 2
    return 1 if minor == 1 else 0


def score_churn(count):
    if int(count) != count or count < 0:
        raise ValueError('amendment count must be a nonnegative integer')
    return min(int(count), 4)
