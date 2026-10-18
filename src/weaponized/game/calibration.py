"""Empirical-to-game measurement guards and reduced-form transition estimation.

No empirical fit is supplied with this module. A caller must provide measured
domestic capability or feasible delivered service and its uncertainty; effective
foreign-plus-domestic semiconductor availability is deliberately not accepted.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares


def domestic_state(layer_capability,essential_layers):
    """Literal domestic bottleneck; missing essential evidence stays missing."""
    if not essential_layers:
        raise ValueError("A registered nonempty architecture is required")
    values=[layer_capability.get(layer) for layer in essential_layers]
    if any(value is None for value in values):return None
    values=np.asarray(values,float)
    if not np.isfinite(values).all() or np.any(values<0) or np.any(values>1):
        raise ValueError("Domestic capabilities must be finite bounded scores")
    return {"state":float(values.min()),"binding_layers":[essential_layers[j] for j in np.flatnonzero(values==values.min())],
            "measure":"domestic_functional_capability_not_effective_availability"}


def resilience_state(delivered,demand,weights):
    """Weighted delivered-service shares from a separately validated China-free LP.

    This function cannot validate routes, recipes or origin. Callers must supply
    the LP exclusion/version provenance; raw capacity coverage is not an input.
    """
    delivered,demand,weights=map(lambda x:np.asarray(x,float),(delivered,demand,weights))
    if delivered.shape!=demand.shape or weights.shape!=demand.shape:
        raise ValueError("Grade dimensions differ")
    if not np.isfinite(np.r_[delivered,demand,weights]).all() or np.any(demand<=0) or np.any(delivered<0) or np.any(delivered>demand+1e-10) or np.any(weights<0) or not np.isclose(weights.sum(),1):
        raise ValueError("Require feasible bounded service, positive demand and normalized frozen weights")
    return float(np.sum(weights*delivered/demand))


def simulate_scalar_transition(controls,initial_state,initial_pipeline,g,beta,depreciation,kappa,delta=.25):
    """Integrate full changing-pipeline bounded law for piecewise constant controls."""
    controls=np.asarray(controls,float)
    if not np.isfinite(controls).all() or np.any(controls<0) or np.any(controls>1):
        raise ValueError("Bounded observed controls required")
    if min(g,kappa,delta)<=0 or depreciation<0 or not 0<=initial_state<=1 or not 0<=initial_pipeline<=1:
        raise ValueError("Invalid transition primitives or initial conditions")
    states=[initial_state];pipelines=[initial_pipeline]
    for control in controls:
        def field(t,z):
            return [g*np.exp(beta*z[1])*(1-z[0])-depreciation*z[0],kappa*(control-z[1])]
        solution=solve_ivp(field,(0,delta),[states[-1],pipelines[-1]],rtol=1e-9,atol=1e-11)
        if not solution.success:raise RuntimeError(solution.message)
        states.append(solution.y[0,-1]);pipelines.append(solution.y[1,-1])
    return np.asarray(states),np.asarray(pipelines)


def fit_scalar_transition(controls,observed,sigma,initial_pipeline,classification,delta=.25,starts=3,seed=101):
    """Measurement-error-weighted multistart fit with local identification diagnostics.

    This conditional least-squares fit treats the observed initial state and
    control series as known. It does not account for serial error or endogenous
    policy and does not identify causal restriction effects. No confidence
    interval is returned without an independently justified observation model.
    """
    if classification not in ("empirical_descriptive_fit","synthetic_recovery_test"):
        raise ValueError("An explicit empirical-versus-synthetic classification is required")
    observed=np.asarray(observed,float);sigma=np.asarray(sigma,float);controls=np.asarray(controls,float)
    if observed.shape!=(controls.size+1,) or sigma.shape!=observed.shape or controls.size<8:
        raise ValueError("At least eight transitions with aligned observations and uncertainties required")
    if not np.isfinite(np.r_[observed,sigma]).all() or np.any(observed<0) or np.any(observed>1) or np.any(sigma<=0):
        raise ValueError("Bounded measured states and positive uncertainties required")
    def residual(theta):
        g,depreciation,kappa=np.exp(theta[[0,2,3]])
        prediction,_=simulate_scalar_transition(controls,observed[0],initial_pipeline,g,theta[1],depreciation,kappa,delta)
        return (prediction[1:]-observed[1:])/sigma[1:]
    rng=np.random.default_rng(seed);results=[]
    for start in range(starts):
        initial=np.array([np.log(.12),.5,np.log(.08),np.log(.5)])
        if start:initial+=rng.normal(0,.5,4)
        result=least_squares(residual,initial,bounds=([-9,-5,-12,-7],[1,5,1,3]),
                             ftol=1e-10,xtol=1e-10,gtol=1e-10,max_nfev=500)
        results.append(result)
    best=min(results,key=lambda r:np.sum(r.fun*r.fun));singular=np.linalg.svd(best.jac,compute_uv=False)
    rank=int(np.sum(singular>max(singular[0]*1e-6,1e-8)))
    theta=best.x;estimates={"g":float(np.exp(theta[0])),"beta":float(theta[1]),
                          "depreciation":float(np.exp(theta[2])),"kappa":float(np.exp(theta[3]))}
    return {"classification":classification,"estimates":estimates,"weighted_sse":float(best.fun@best.fun),
            "success":bool(best.success),"jacobian_singular_values":singular.tolist(),"local_rank":rank,
            "condition_number":float(singular[0]/singular[-1]) if singular[-1]>0 else None,
            "identified_causal_effect":False,"local_identification_warning":rank<4,
            "start_objectives":[float(result.fun@result.fun) for result in results],
            "estimated_parameter_order":["log_g","beta","log_depreciation","log_kappa"],
            "bounds_are_numerical_search_limits_not_confidence_intervals":True,
            "limitations":["initial observation and policy controls treated as known","no causal identification from policy endogeneity",
                           "no empirical error-model validation","local rank is not global identification"]}
