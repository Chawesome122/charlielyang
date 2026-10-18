"""Independent ordinal-coder agreement and paired-bootstrap uncertainty."""
import numpy as np


def weighted_kappa(coder_a, coder_b, weighting='quadratic'):
    a, b = np.asarray(coder_a, dtype=float), np.asarray(coder_b, dtype=float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError('paired one-dimensional coder arrays required')
    keep = np.isfinite(a) & np.isfinite(b)
    a, b = a[keep], b[keep]
    if len(a) < 2:
        raise ValueError('at least two independently paired observations required')
    if np.any((a < 0) | (a > 4) | (b < 0) | (b > 4) | (a != a.astype(int)) | (b != b.astype(int))):
        raise ValueError('ordinal categories must be integer 0..4')
    observed = np.zeros((5,5))
    np.add.at(observed, (a.astype(int), b.astype(int)), 1)
    observed /= len(a)
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))
    delta = np.abs(np.arange(5)[:,None] - np.arange(5)[None,:])/4
    if weighting == 'quadratic':
        distance = delta**2
    elif weighting == 'linear':
        distance = delta
    else:
        raise ValueError('weighting must be linear or quadratic')
    expected_disagreement = float((distance*expected).sum())
    return float('nan') if expected_disagreement == 0 else 1 - float((distance*observed).sum())/expected_disagreement


def reliability_report(coder_a, coder_b, *, independent, n_bootstrap=2000, seed=505,
                       weighting='quadratic', target=.75):
    if not independent:
        return {'status': 'BLOCKED', 'reason': 'independent_blinded_second_coder_unavailable', 'kappa': None,
                'raw_agreement': None, 'ci_lower': None, 'ci_upper': None}
    a, b = np.asarray(coder_a, dtype=float), np.asarray(coder_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError('paired arrays differ')
    keep = np.isfinite(a) & np.isfinite(b)
    a, b = a[keep], b[keep]
    kappa = weighted_kappa(a, b, weighting)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(n_bootstrap):
        indices = rng.integers(0,len(a),len(a))
        value = weighted_kappa(a[indices], b[indices], weighting)
        if np.isfinite(value):
            values.append(value)
    lo, hi = np.quantile(values,[.025,.975]) if values else (float('nan'),float('nan'))
    return {'status': 'PASS' if np.isfinite(kappa) and kappa >= target else 'REVISE_AND_INDEPENDENTLY_RECODE',
            'kappa': kappa, 'raw_agreement': float(np.mean(a==b)), 'ci_lower': float(lo), 'ci_upper': float(hi),
            'n_pairs': len(a), 'bootstrap_valid_replicates': len(values), 'bootstrap_requested': n_bootstrap,
            'seed': seed, 'weighting': weighting, 'target': target,
            'ci_method': 'paired_iid_percentile_bootstrap; use source/event block resampling for dependent field data'}
