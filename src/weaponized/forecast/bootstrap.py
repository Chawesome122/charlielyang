"""Project-parent and calendar-origin block resampling."""
import numpy as np


def cluster_bootstrap_indices(cluster_labels, rng, n_bootstrap=1000):
    labels = np.asarray(cluster_labels)
    groups = np.unique(labels)
    if len(groups) < 2:
        raise ValueError("At least two independent clusters required")
    members = {g: np.flatnonzero(labels == g) for g in groups}
    return [np.concatenate([members[g] for g in rng.choice(groups, len(groups), replace=True)])
        for _ in range(n_bootstrap)]


def two_way_pigeonhole_weights(project_parents, calendar_origins, rng, n_bootstrap=1000):
    """Crossed cluster resampling weights, not independent-row bootstrap.

    Resample each dimension then multiply its cluster multiplicities. Small
    project/origin cluster counts still prevent reliable asymptotic inference.
    """
    parents, origins = np.asarray(project_parents), np.asarray(calendar_origins)
    if len(parents) != len(origins):
        raise ValueError("Cluster labels must align")
    p, pi = np.unique(parents, return_inverse=True)
    o, oi = np.unique(origins, return_inverse=True)
    if min(len(p), len(o)) < 2:
        raise ValueError("Need >=2 project parents and >=2 calendar origins")
    output = []
    for _ in range(n_bootstrap):
        pw = np.bincount(rng.integers(len(p), size=len(p)), minlength=len(p))
        ow = np.bincount(rng.integers(len(o), size=len(o)), minlength=len(o))
        output.append(pw[pi] * ow[oi])
    return np.asarray(output)
