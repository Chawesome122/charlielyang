"""Independent unchanged-criterion checks of saved accelerated policy arrays."""
import numpy as np
from .hjb import build_generator,policy_deviation_gaps
from .primitives import payoffs


def audit_saved_response(grid,p,u,c,vu,vc,reported_status):
    fields=[np.asarray(x,dtype=float).ravel() for x in [u,c,vu,vc]]
    if any(a.shape!=(grid.count,) or not np.isfinite(a).all() for a in fields):
        raise ValueError('Nonfinite or incorrectly sized saved fields')
    u,c,vu,vc=fields
    if np.any((u<0)|(u>1)|(c<0)|(c>1)):raise ValueError('Saved policy outside control box')
    if reported_status not in {'verified_finite_grid_candidate','not_solved'}:raise ValueError('Unknown reported status')
    generator=build_generator(grid,p,u,c);reward=payoffs(grid.states,u,c,p)
    residual=[float(np.max(abs(rho*v-r-generator@v))) for rho,v,r in zip([p.rho_u,p.rho_c],[vu,vc],reward)]
    gu,gc,bu,bc=policy_deviation_gaps(grid,p,[vu,vc],u,c)
    gap=float(max(gu.max(),gc.max()));action=float(max(np.max(abs(bu-u)),np.max(abs(bc-c))))
    passed=gap<=1e-8 and action<=1e-7 and all(x<=1e-8*(1+np.max(abs(r))) for x,r in zip(residual,reward))
    if passed!=(reported_status=='verified_finite_grid_candidate'):
        raise ValueError('Claimed status disagrees with independently recomputed original Nash thresholds')
    return dict(status_consistent=True,accepted_finite_grid_candidate=bool(passed),max_unilateral_gain=gap,
                best_response_action_residual=action,hjb_residuals=residual,
                continuous_mpe_certified=False,nonexistence_proved=False)


def decode_saved_fields(blob,expected_sha256,grid):
    """Hash and parse exactly one NPZ byte snapshot, rejecting substituted axes."""
    import hashlib
    import io
    if hashlib.sha256(blob).hexdigest()!=expected_sha256:raise ValueError('Archive checksum mismatch')
    with np.load(io.BytesIO(blob)) as data:
        if not np.array_equal(data['axis'],grid.axes[0]):raise ValueError('Saved grid axis mismatch')
        return [data[k].ravel().copy() for k in ['u','c','value_u','value_c']]


def verify_source_manifest(root,manifest):
    """Refuse changed model/method/reference files rather than reusing a label."""
    import hashlib
    for path,digest in manifest.items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Registered source checksum mismatch: {path}')
    return len(manifest)
