"""Full feedback Jacobians, distinct from fixed-policy stability."""
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import root
from .primitives import dynamics


def interpolated_policy(grid,u,c):
    iu=RegularGridInterpolator(grid.axes,u.reshape(grid.shape),bounds_error=True)
    ic=RegularGridInterpolator(grid.axes,c.reshape(grid.shape),bounds_error=True)
    def policy(state):
        return float(iu(np.asarray(state)[None,:])[0]),float(ic(np.asarray(state)[None,:])[0])
    return policy


def closed_loop_jacobian(state,policy,p,step=1e-5):
    """Difference the composite field, thereby including policy derivatives.

    Grid interpolation is only piecewise differentiable. At a grid knot a central
    secant is not a unique derivative; caller must record that limitation.
    """
    state=np.asarray(state,float);jacobian=np.empty((4,4))
    for j in range(4):
        lo=state.copy();hi=state.copy();lo[j]=max(0,state[j]-step);hi[j]=min(1,state[j]+step)
        ulo,clo=policy(lo);uhi,chi=policy(hi)
        jacobian[:,j]=(dynamics(hi,uhi,chi,p)-dynamics(lo,ulo,clo,p))/(hi[j]-lo[j])
    return jacobian


def feedback_stationary_point(grid,u,c,p,guess=None):
    policy=interpolated_policy(grid,u,c)
    def field(s):
        # Unbounded root iterates use a projected field only to evaluate trial
        # values; any accepted root must lie in the cube and pass original drift.
        clipped=np.clip(s,0,1);us,cn=policy(clipped)
        return dynamics(clipped,us,cn,p)+(s-clipped)
    solved=root(field,np.full(4,.5) if guess is None else guess)
    state=solved.x
    valid=bool(solved.success and np.all(state>=0) and np.all(state<=1) and np.max(abs(field(state)))<1e-8)
    result={"verified_stationary_point":valid,"state":state.tolist(),"drift_residual":float(np.max(abs(field(state))))}
    if valid:
        jacobian=closed_loop_jacobian(state,policy,p)
        eig=np.linalg.eigvals(jacobian)
        knot_distance=float(np.min(abs(state[:,None]-grid.axes[0][None,:])))
        smooth_neighborhood=knot_distance>2e-5
        result.update({"full_closed_loop_jacobian":jacobian.tolist(),"eigenvalues_real":eig.real.tolist(),
                       "eigenvalues_imag":eig.imag.tolist(),
                       "locally_stable":bool(np.max(eig.real)<0) if smooth_neighborhood else None,
                       "stability_status":("locally_stable_interpolated_policy" if np.max(eig.real)<0 else "not_locally_stable_linearization") if smooth_neighborhood else "inconclusive_at_interpolation_knot",
                       "jacobian_is_local_derivative":smooth_neighborhood,
                       "distance_to_grid_knot":knot_distance,
                       "nonsmooth_warning":None if smooth_neighborhood else "Central secant spectrum at an interpolation knot cannot establish local stability; one-sided or nonsmooth analysis required.",
                       "interpretation":"piecewise_multilinear_interpolated_scenario_policy_not_exact_continuum_equilibrium"})
    return result
