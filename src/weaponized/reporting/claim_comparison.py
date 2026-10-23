"""Compare scientific claim provenance while preserving per-run exact hashes.

The saved-game audit intentionally records held-out evaluation runtimes. Only
those explicitly located performance fields can differ; all other evidence bytes
and all scientific JSON fields must match exactly. No numerical tolerance is used.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

TIMED_AUDIT = 'outputs/scenario/game/independent_saved_candidate_audit.json'


def claim_payloads(root, claims):
    root = Path(root).resolve()
    payloads = {}
    for claim in claims:
        path = root / claim['evidence']
        if not path.resolve().is_relative_to(root):
            raise ValueError('Claim evidence must remain inside the research repository')
        payloads[claim['evidence']] = path.read_bytes()
    return payloads


def scientific_audit_bytes(payload):
    """Omit only grid_refinement[i].heldout_policy_evaluation.elapsed_seconds."""
    value = json.loads(payload)
    value = copy.deepcopy(value)
    refinements = value.get('grid_refinement')
    if not isinstance(refinements, list) or not refinements:
        raise ValueError('Expected explicit grid-refinement evaluation records')
    omitted = []
    for i, row in enumerate(refinements):
        evaluation = row.get('heldout_policy_evaluation')
        if not isinstance(evaluation, dict) or 'elapsed_seconds' not in evaluation:
            raise ValueError('Expected explicitly located performance clock')
        clock = evaluation.pop('elapsed_seconds')
        if isinstance(clock, bool) or not isinstance(clock, (int, float)) or not math.isfinite(clock) or clock < 0:
            raise ValueError('Performance clock must be finite and nonnegative')
        omitted.append(f'grid_refinement[{i}].heldout_policy_evaluation.elapsed_seconds')
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode(), omitted


def compare_claim_manifests(before, before_payloads, after, after_payloads):
    if not before or len(before) != len(after):
        raise ValueError('Claim counts differ or are empty')
    timed = []; seen = set()
    for old, new in zip(before, after, strict=True):
        if set(old) != {'claim','classification','evidence','sha256'} or set(new) != set(old):
            raise ValueError('Unexpected claim-manifest schema')
        if {k:v for k,v in old.items() if k!='sha256'} != {k:v for k,v in new.items() if k!='sha256'}:
            raise ValueError('Claim meaning, order, class or evidence reference changed')
        path = old['evidence'];seen.add(path)
        for claim, payloads in [(old, before_payloads), (new, after_payloads)]:
            digest = claim['sha256']
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or hashlib.sha256(payloads[path]).hexdigest() != digest:
                raise ValueError('Per-environment exact evidence SHA256 is invalid: ' + path)
        a, b = before_payloads[path], after_payloads[path]
        if path == TIMED_AUDIT:
            left, fields = scientific_audit_bytes(a)
            right, other_fields = scientific_audit_bytes(b)
            if fields != other_fields or left != right:
                raise ValueError('Scientific game-audit fields changed')
            timed.append(dict(evidence=path, only_excluded_fields=fields,
                              before_sha256=old['sha256'], after_sha256=new['sha256'],
                              scientific_fields_exactly_identical=True))
        elif a != b:
            raise ValueError('Ordinary claim evidence bytes changed: ' + path)
    return dict(passed=True, claims=len(before), distinct_evidence_files=len(seen),
                per_environment_exact_SHA256_checks=2*len(before),
                raw_claim_manifests_identical=before==after,
                scientific_claims_exactly_identical=True,
                numerical_acceptance_tolerances_changed=False,
                timing_bearing_evidence=timed)
