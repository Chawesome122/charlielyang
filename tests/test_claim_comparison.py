"""A performance clock must never excuse a changed scientific result."""
import copy
import hashlib
import json

import pytest

from weaponized.reporting.claim_comparison import TIMED_AUDIT, compare_claim_manifests


def manifest(path, payload):
    return [dict(claim='fixture only',classification='synthetic_test_fixture',evidence=path,
                 sha256=hashlib.sha256(payload).hexdigest())]


def payload(clock=1., residual=.001, certified=False):
    return json.dumps(dict(continuous_mpe_certified=certified,grid_refinement=[dict(
        heldout_policy_evaluation=dict(elapsed_seconds=clock,residual=residual))])).encode()


def compare(a,b,path=TIMED_AUDIT):
    return compare_claim_manifests(manifest(path,a),{path:a},manifest(path,b),{path:b})


def test_runtime_difference_keeps_both_exact_local_hashes():
    result=compare(payload(clock=1.),payload(clock=2.))
    assert result['passed'] and not result['raw_claim_manifests_identical']
    assert result['scientific_claims_exactly_identical']
    assert result['per_environment_exact_SHA256_checks']==2
    assert result['timing_bearing_evidence'][0]['only_excluded_fields']==[
        'grid_refinement[0].heldout_policy_evaluation.elapsed_seconds']
    assert not result['numerical_acceptance_tolerances_changed']


@pytest.mark.parametrize('changed',[dict(residual=.0010001),dict(certified=True)])
def test_any_changed_scientific_result_is_rejected(changed):
    with pytest.raises(ValueError,match='Scientific game-audit fields'):
        compare(payload(),payload(clock=2.,**changed))


def test_ordinary_source_changes_cannot_be_normalized():
    with pytest.raises(ValueError,match='Ordinary claim evidence bytes'):
        compare(b'0.2',b'0.3',path='data/processed/fixture.csv')


def test_exact_local_digest_is_still_required():
    a=payload();old=manifest(TIMED_AUDIT,a);new=copy.deepcopy(old);new[0]['sha256']='0'*64
    with pytest.raises(ValueError,match='exact evidence SHA256'):
        compare_claim_manifests(old,{TIMED_AUDIT:a},new,{TIMED_AUDIT:a})


@pytest.mark.parametrize('clock',[-1,float('nan'),True])
def test_invalid_performance_clocks_are_rejected(clock):
    with pytest.raises(ValueError,match='Performance clock'):
        compare(payload(),payload(clock=clock))
