"""Prespecified arithmetic sensitivity; no empirical intent interpretation."""
import numpy as np
import pandas as pd
from .coding import CODES
from .index import aggregate_scores, spoi_daily, quarterly_spoi


def alternative_weights(scores):
    principal = aggregate_scores(scores)
    equal_pillars = aggregate_scores(scores, weights={'disclosure':1/3,'predictability':1/3,'clarity':1/3})
    complete = all(k in scores and scores[k] is not None and not pd.isna(scores[k]) for k in CODES)
    return {'principal': principal['spoi'], 'equal_pillars': equal_pillars['spoi'],
            'equal_ten_indicators': 25*np.mean([scores[k] for k in CODES]) if complete else float('nan'),
            'equal_ten_reason': 'complete_ten_indicators' if complete else 'requires_complete_ten_indicator_denominator'}


def window_sensitivity(obligations, legal_events, source_events, settings, start, end):
    rows = []
    for memory in (30,90,180):
        for grace in (0,30,90):
            config = {**settings, 'event_memory_days':memory, 'release_grace_days':grace}
            daily = spoi_daily(obligations,legal_events,source_events,config,start,end)
            quarter = quarterly_spoi(daily)
            quarter['event_memory_days'] = memory
            quarter['release_grace_days'] = grace
            rows.append(quarter)
    return pd.concat(rows,ignore_index=True)


def factor_eligibility(daily):
    """A descriptive factor cannot be fitted when ten-indicator rows are absent."""
    complete = daily[list(CODES)].dropna()
    varying = int((complete.nunique() > 1).sum())
    return {'status':'BLOCKED' if len(complete)<30 or varying<2 else 'DESIGN_REVIEW_REQUIRED',
            'complete_rows':len(complete), 'varying_indicators':varying,
            'reason':'requires_sufficient_complete_observations_and_ordinal_factor_model_validation'}
