"""Safeguarded search checks against exact global HJB response/evaluation."""
import numpy as np
import pytest
from weaponized.game.hjb import StateGrid,policy_deviation_gaps,evaluate_policies
from weaponized.game.primitives import GameParameters
from weaponized.game.safeguarded_iteration import anderson_proposal,evaluated_response,accepted_response,solve_safeguarded_game


def test_affine_map_multisecant_step_finds_exact_scalar_root():
    # T(x)=.2+.5x, root .4; the first relaxed step is .2.
    proposal,diagnostic=anderson_proposal([np.array([0.]),np.array([.2])],[np.array([.2]),np.array([.1])],ridge=0)
    assert abs(proposal[0]-.4)<1e-12 and diagnostic['memory_used']==1


def test_box_projection_is_admissible_but_does_not_bypass_nash_tests():
    proposal,_=anderson_proposal([np.array([.2,.8])],[np.array([-10.,10.])])
    assert np.array_equal(proposal,[0,1])
    response={'gap':1e-10,'action':1e-4,'evaluation':{'players':[{'linear_residual_inf':1e-12,'reward_inf':1}]}}
    assert not accepted_response(response)


def test_evaluated_map_matches_independent_original_hjb_call():
    grid=StateGrid(3);p=GameParameters(beta_c=-.7,beta_u=-.7);actions=np.r_[np.full(grid.count,.4),np.full(grid.count,.7)]
    response=evaluated_response(grid,p,actions)
    values,_=evaluate_policies(grid,p,actions[:grid.count],actions[grid.count:])
    gu,gc,bu,bc=policy_deviation_gaps(grid,p,values,actions[:grid.count],actions[grid.count:])
    assert response['gap']==max(gu.max(),gc.max())
    assert np.allclose(response['residual'],np.r_[bu,bc]-actions,atol=1e-12)


def test_finite_grid_solution_is_rechecked_not_accepted_on_small_iterate_motion():
    grid=StateGrid(3);p=GameParameters(beta_c=0,beta_u=0,q_u=0,q_c=0)
    result=solve_safeguarded_game(grid,p,max_iterations=70)
    assert result['status']=='verified_finite_grid_candidate'
    assert result['max_deviation_gain']<=1e-8 and result['best_response_action_residual']<=1e-7
    assert not result['continuous_mpe_certified']


def test_budget_exhaustion_preserves_failed_arrays_without_looser_thresholds():
    result=solve_safeguarded_game(3,GameParameters(beta_c=-.7,beta_u=-.7),max_iterations=1)
    assert result['status']=='not_solved'
    assert np.isfinite(result['u']).all() and np.isfinite(result['values']).all()
    assert result['termination_reason']=='iteration_budget_exhausted'


def test_invalid_policy_and_solver_settings_are_rejected():
    with pytest.raises(ValueError):anderson_proposal([],[])
    with pytest.raises(ValueError):solve_safeguarded_game(3,GameParameters(),damping=0)
    with pytest.raises(ValueError):evaluated_response(StateGrid(3),GameParameters(),np.ones(162)*1.01)


def test_independent_archive_audit_rejects_false_acceptance_and_stale_values():
    from weaponized.game.safeguarded_archive import audit_saved_response
    g=StateGrid(3);p=GameParameters(beta_c=-.7,beta_u=-.7)
    u=np.zeros(g.count);c=np.zeros(g.count);values,_=evaluate_policies(g,p,u,c)
    honest=audit_saved_response(g,p,u,c,*values,'not_solved')
    assert honest['status_consistent'] and not honest['accepted_finite_grid_candidate']
    with pytest.raises(ValueError,match='Claimed status'):
        audit_saved_response(g,p,u,c,*values,'verified_finite_grid_candidate')
    solved=solve_safeguarded_game(g,GameParameters(beta_c=0,beta_u=0,q_u=0,q_c=0),max_iterations=70)
    sp=GameParameters(beta_c=0,beta_u=0,q_u=0,q_c=0)
    with pytest.raises(ValueError,match='Claimed status'):
        audit_saved_response(g,sp,solved['u'],solved['c'],solved['values'][0]+1,solved['values'][1],'verified_finite_grid_candidate')


def test_independent_archive_audit_rejects_unknown_status_and_nonfinite_fields():
    from weaponized.game.safeguarded_archive import audit_saved_response
    g=StateGrid(3);p=GameParameters();z=np.zeros(g.count)
    with pytest.raises(ValueError,match='Unknown reported status'):audit_saved_response(g,p,z,z,z,z,'converged')
    bad=z.copy();bad[0]=np.nan
    with pytest.raises(ValueError,match='Nonfinite'):audit_saved_response(g,p,z,z,bad,z,'not_solved')


def test_verified_archive_bytes_reject_corruption_and_wrong_axis():
    import hashlib,io
    from weaponized.game.safeguarded_archive import decode_saved_fields
    g=StateGrid(3);memory=io.BytesIO();z=np.zeros(g.shape)
    np.savez_compressed(memory,u=z,c=z,value_u=z,value_c=z,axis=g.axes[0]);blob=memory.getvalue();sha=hashlib.sha256(blob).hexdigest()
    assert len(decode_saved_fields(blob,sha,g))==4
    with pytest.raises(ValueError,match='checksum'):decode_saved_fields(blob+b'corruption',sha,g)
    memory=io.BytesIO();np.savez_compressed(memory,u=z,c=z,value_u=z,value_c=z,axis=np.array([0.,.4,1.]))
    changed=memory.getvalue()
    with pytest.raises(ValueError,match='axis'):decode_saved_fields(changed,hashlib.sha256(changed).hexdigest(),g)


def test_reference_source_guard_refuses_model_substitution(tmp_path):
    import hashlib
    from weaponized.game.safeguarded_archive import verify_source_manifest
    p=tmp_path/'model.py';p.write_text('original model')
    expected={'model.py':hashlib.sha256(p.read_bytes()).hexdigest()}
    assert verify_source_manifest(tmp_path,expected)==1
    p.write_text('changed model')
    with pytest.raises(ValueError,match='source checksum'):verify_source_manifest(tmp_path,expected)
