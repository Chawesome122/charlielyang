"""Monotone state-constrained finite-state approximation to the four-state HJB.

The generator is a continuous-time Markov chain approximation, NOT the literal
deterministic ODE on grid nodes. Artificial grid diffusion vanishes with mesh size.
Because own action changes pipeline drift sign, its discrete Hamiltonian is
piecewise quadratic; policy improvement must optimize BOTH directional pieces.
"""
from dataclasses import dataclass
import itertools
import time
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import bicgstab, gmres, LinearOperator
from .primitives import dynamics, payoffs, GameParameters


@dataclass
class StateGrid:
    size: int

    def __post_init__(self):
        if self.size < 3:
            raise ValueError("At least three nodes per dimension required")
        self.axes=tuple(np.linspace(0,1,self.size) for _ in range(4))
        self.shape=(self.size,)*4
        self.spacing=1/(self.size-1)
        self.states=np.stack(np.meshgrid(*self.axes,indexing="ij"),axis=-1).reshape(-1,4)
        self.count=self.size**4
        self.strides=np.array([self.size**3,self.size**2,self.size,1])

    def derivative_pair(self, value, axis):
        v=np.asarray(value).reshape(self.shape)
        forward=np.zeros_like(v); backward=np.zeros_like(v)
        lo=[slice(None)]*4; hi=lo.copy()
        lo[axis]=slice(0,-1); hi[axis]=slice(1,None)
        diff=(v[tuple(hi)]-v[tuple(lo)])/self.spacing
        forward[tuple(lo)]=diff; backward[tuple(hi)]=diff
        # Missing outward differences will always multiply zero rates. Keeping
        # them zero prevents artificial extrapolation in boundary maximization.
        return backward.ravel(), forward.ravel()


def build_generator(grid: StateGrid, p: GameParameters, u, c):
    drift=dynamics(grid.states,u,c,p)
    rows=np.arange(grid.count)
    all_rows=[]; all_cols=[]; all_data=[]
    diag=np.zeros(grid.count)
    for dim,stride in enumerate(grid.strides):
        for direction in (-1,1):
            rate=np.maximum(direction*drift[:,dim],0)/grid.spacing
            boundary=grid.states[:,dim] == (0 if direction<0 else 1)
            if np.any(rate[boundary]>1e-10):
                raise ValueError("Outward drift violates state constraints")
            rate[boundary]=0
            selected=rate>0
            all_rows.append(rows[selected]); all_cols.append(rows[selected]+direction*stride)
            all_data.append(rate[selected]); diag-=rate
    all_rows.append(rows);all_cols.append(rows);all_data.append(diag)
    generator=sparse.coo_matrix((np.concatenate(all_data),(np.concatenate(all_rows),np.concatenate(all_cols))),
                                shape=(grid.count,grid.count)).tocsr()
    return generator


def evaluate_policies(grid, p, u, c, initial_values=None, linear_rtol=1e-11):
    started=time.perf_counter()
    generator=build_generator(grid,p,u,c)
    rewards=payoffs(grid.states,u,c,p)
    values=[]; diagnostics=[]
    for i,rho in enumerate((p.rho_u,p.rho_c)):
        matrix=-generator+sparse.eye(grid.count,format="csr")*rho
        preconditioner=LinearOperator(matrix.shape,matvec=lambda x,d=matrix.diagonal():x/d)
        iterations=[0]
        def callback(_): iterations[0]+=1
        value,code=bicgstab(matrix,rewards[i],x0=None if initial_values is None else initial_values[i],
                            M=preconditioner,rtol=linear_rtol,atol=1e-13,maxiter=3000,callback=callback)
        residual=float(np.max(np.abs(matrix@value-rewards[i])))
        first_code = int(code)
        method = "bicgstab_jacobi"
        if code != 0 or not np.isfinite(value).all():
            # BiCGSTAB may stagnate on nearly reducible directed-grid operators.
            # The discounted matrix remains a nonsingular M-matrix. Restarted
            # GMRES is a supported alternative, with the original residual still
            # independently checked below; never relax the acceptance tolerance.
            method = "gmres_jacobi_after_bicgstab_failure"
            fallback_start = value if np.isfinite(value).all() else None
            value, code = gmres(matrix,rewards[i],x0=fallback_start,M=preconditioner,
                                rtol=linear_rtol,atol=1e-13,restart=80,maxiter=150,
                                callback=callback,callback_type="legacy")
            residual=float(np.max(np.abs(matrix@value-rewards[i])))
        if code != 0 or not np.isfinite(value).all():
            raise RuntimeError(f"Sparse policy evaluation failed: code={code}, residual={residual}")
        values.append(value)
        diagnostics.append({"bicgstab_code":first_code,"final_solver_code":int(code),"linear_method":method,"iterations":iterations[0],"linear_residual_inf":residual,
                            "reward_inf":float(np.max(np.abs(rewards[i])))})
    return values, {"players":diagnostics,"matrix_nnz":int(generator.nnz),
                    "sparse_bytes":int(generator.data.nbytes+generator.indices.nbytes+generator.indptr.nbytes),
                    "elapsed_seconds":time.perf_counter()-started}


def own_hamiltonian(action, other, current_pipeline, base, cost, coupling, kappa, minus, plus):
    derivative=np.where(action>=current_pipeline,plus,minus)
    return base*action-.5*cost*action*action+coupling*action*other+kappa*(action-current_pipeline)*derivative


def piecewise_best_response(other, pipeline, base, cost, coupling, kappa, minus, plus):
    """Exact global maximum across both drift regions and their common kink."""
    candidates=np.stack((np.zeros_like(pipeline),pipeline,np.ones_like(pipeline),
                         np.clip((base+coupling*other+kappa*minus)/cost,0,pipeline),
                         np.clip((base+coupling*other+kappa*plus)/cost,pipeline,1)))
    scores=own_hamiltonian(candidates,other,pipeline,base,cost,coupling,kappa,minus,plus)
    argmax=np.argmax(scores,axis=0)
    return np.take_along_axis(candidates,argmax[None,:],axis=0)[0],np.max(scores,axis=0)


def policy_deviation_gaps(grid,p,values,u,c):
    x,y,m,n=grid.states.T
    um,up=grid.derivative_pair(values[0],2); cm,cp=grid.derivative_pair(values[1],3)
    us,best_u=piecewise_best_response(c,m,p.a_u*(1-x),p.k_u,p.q_u,p.kappa_c,um,up)
    cs,best_c=piecewise_best_response(u,n,p.a_c*(1-y),p.k_c,p.q_c,p.kappa_u,cm,cp)
    current_u=own_hamiltonian(u,c,m,p.a_u*(1-x),p.k_u,p.q_u,p.kappa_c,um,up)
    current_c=own_hamiltonian(c,u,n,p.a_c*(1-y),p.k_c,p.q_c,p.kappa_u,cm,cp)
    return np.maximum(0,best_u-current_u),np.maximum(0,best_c-current_c),us,cs


def improve_policies(grid,p,values,u_old,c_old,tol=1e-10):
    """Enumerate exact 5x5 piecewise active statuses at each grid state.

    Each player is at 0, pipeline kink, 1, lower-piece interior, or upper-piece
    interior. All feasible algebraic pairs are tested against GLOBAL unilateral
    maxima; local KKT is insufficient at a nonconcave finite-difference kink.
    Returns failures rather than silently treating an approximate response as Nash.
    The analytic nine-regime solver lives separately in active_set.py.
    """
    x,y,m,n=grid.states.T
    um,up=grid.derivative_pair(values[0],2); cm,cp=grid.derivative_pair(values[1],3)
    base_u=p.a_u*(1-x);base_c=p.a_c*(1-y)
    mu=(None,None,None,base_u+p.kappa_c*um,base_u+p.kappa_c*up)
    mc=(None,None,None,base_c+p.kappa_u*cm,base_c+p.kappa_u*cp)
    fixed_u=(np.zeros_like(m),m,np.ones_like(m));fixed_c=(np.zeros_like(n),n,np.ones_like(n))
    chosen_u=u_old.copy();chosen_c=c_old.copy()
    distance=np.full(grid.count,np.inf);chosen_gap=np.full(grid.count,np.inf)
    multiplicity=np.zeros(grid.count,dtype=np.int16)
    best_fallback=np.full(grid.count,np.inf);fallback_u=u_old.copy();fallback_c=c_old.copy()
    determinant=p.k_u*p.k_c-p.q_u*p.q_c
    for ui,ci in itertools.product(range(5),repeat=2):
        if ui<3 and ci<3:
            u,c=fixed_u[ui],fixed_c[ci]
        elif ui<3:
            u=fixed_u[ui];c=(mc[ci]+p.q_c*u)/p.k_c
        elif ci<3:
            c=fixed_c[ci];u=(mu[ui]+p.q_u*c)/p.k_u
        else:
            if abs(determinant)<1e-12:
                # No finite isolated enumeration is complete at this singularity.
                continue
            u=(p.k_c*mu[ui]+p.q_u*mc[ci])/determinant
            c=(p.k_u*mc[ci]+p.q_c*mu[ui])/determinant
        valid=(u>=-tol)&(u<=1+tol)&(c>=-tol)&(c<=1+tol)
        if ui==3:valid&=u<=m+tol
        if ui==4:valid&=u>=m-tol
        if ci==3:valid&=c<=n+tol
        if ci==4:valid&=c>=n-tol
        if not np.any(valid): continue
        u=np.clip(u,0,1);c=np.clip(c,0,1)
        _,bu=piecewise_best_response(c,m,base_u,p.k_u,p.q_u,p.kappa_c,um,up)
        _,bc=piecewise_best_response(u,n,base_c,p.k_c,p.q_c,p.kappa_u,cm,cp)
        gu=np.maximum(0,bu-own_hamiltonian(u,c,m,base_u,p.k_u,p.q_u,p.kappa_c,um,up))
        gc=np.maximum(0,bc-own_hamiltonian(c,u,n,base_c,p.k_c,p.q_c,p.kappa_u,cm,cp))
        gap=np.maximum(gu,gc)
        improved=valid&(gap<best_fallback)
        fallback_u[improved]=u[improved];fallback_c[improved]=c[improved];best_fallback[improved]=gap[improved]
        accepted=valid&(gap<=tol)
        multiplicity+=accepted
        change=(u-u_old)**2+(c-c_old)**2
        # Prefer a genuinely maximizing root over a nearby kink whose tiny
        # payoff loss happens to pass tolerance. Distance alone can stall with
        # action error sqrt(tolerance), above the required action threshold.
        choose=accepted&((gap<chosen_gap-1e-16)|((abs(gap-chosen_gap)<=1e-16)&(change<distance)))
        chosen_u[choose]=u[choose];chosen_c[choose]=c[choose];distance[choose]=change[choose]
        chosen_gap[choose]=gap[choose]
    missing=~np.isfinite(distance)
    chosen_u[missing]=fallback_u[missing];chosen_c[missing]=fallback_c[missing]
    return chosen_u,chosen_c,{"no_verified_pure_action_candidate_nodes":int(missing.sum()),
                             "max_fallback_gap":float(np.max(best_fallback[missing])) if np.any(missing) else 0.,
                             "singular_interior_enumeration":bool(abs(determinant)<1e-12)}
