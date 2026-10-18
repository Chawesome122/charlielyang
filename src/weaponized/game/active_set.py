"""Exact simultaneous statewise action Nash, including singular solution sets."""
from dataclasses import dataclass
import itertools
import numpy as np


@dataclass(frozen=True)
class ActionSolution:
    u: float
    c: float
    regimes: tuple[str, ...]
    best_response_residual: float
    # A segment denotes all convex combinations of its endpoints, not just this representative.
    continuum_endpoints: tuple[tuple[float, float], tuple[float, float]] | None = None


def conditional_best_responses(u, c, mu, mc, k_u, k_c, q_u, q_c):
    return np.clip((mu+q_u*np.asarray(c))/k_u,0,1), np.clip((mc+q_c*np.asarray(u))/k_c,0,1)


def solve_stage_nash(mu, mc, k_u, k_c, q_u, q_c, tol=1e-10):
    """Enumerate nine regimes. Equality candidates are de-duplicated.

    Singular interior equations can have an entire line segment of equilibria;
    return one midpoint with explicit segment endpoints rather than claim uniqueness.
    """
    if k_u <= 0 or k_c <= 0 or not np.isfinite([mu,mc,k_u,k_c,q_u,q_c]).all():
        raise ValueError("Finite primitives and positive own-cost curvature required")
    found = []
    def add(u,c,regime,segment=None):
        if not -tol <= u <= 1+tol or not -tol <= c <= 1+tol:
            return
        u,c=float(np.clip(u,0,1)),float(np.clip(c,0,1))
        bu,bc=conditional_best_responses(u,c,mu,mc,k_u,k_c,q_u,q_c)
        residual=float(max(abs(u-bu),abs(c-bc)))
        if residual>tol:
            return
        for i,old in enumerate(found):
            if max(abs(u-old.u),abs(c-old.c))<tol and old.continuum_endpoints==segment:
                found[i]=ActionSolution(u,c,old.regimes+(regime,),residual,segment)
                return
        found.append(ActionSolution(u,c,(regime,),residual,segment))
    for ur,cr in itertools.product(("0","1","I"),repeat=2):
        label=f"{ur}/{cr}"
        if ur != "I" and cr != "I":
            add(float(ur),float(cr),label)
        elif ur=="I" and cr!="I":
            c=float(cr); add((mu+q_u*c)/k_u,c,label)
        elif ur!="I" and cr=="I":
            u=float(ur); add(u,(mc+q_c*u)/k_c,label)
        else:
            determinant=k_u*k_c-q_u*q_c
            if abs(determinant)>tol*max(1,k_u*k_c,abs(q_u*q_c)):
                add((k_c*mu+q_u*mc)/determinant,(k_u*mc+q_c*mu)/determinant,label)
            else:
                # Parameterize c in [0,1], u=(mu+q_u*c)/k_u.
                if abs(mc+q_c*mu/k_u)>tol:
                    continue
                ends=[]
                for c in (0.,1.):
                    u=(mu+q_u*c)/k_u
                    if -tol<=u<=1+tol: ends.append((float(np.clip(u,0,1)),c))
                if abs(q_u)>tol:
                    for u in (0.,1.):
                        c=(k_u*u-mu)/q_u
                        if -tol<=c<=1+tol: ends.append((u,float(np.clip(c,0,1))))
                if ends:
                    ends=sorted(set(ends),key=lambda pair:pair[1]); lo,hi=ends[0],ends[-1]
                    add((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,label,(lo,hi))
    if not found:
        raise ArithmeticError("No statewise equilibrium found; inspect conditioning/tolerance")
    return found
