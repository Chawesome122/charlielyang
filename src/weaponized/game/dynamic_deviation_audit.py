"""Fixed-opponent discounted-MDP verification for the finite-state game.

These are continuous-action CTMC approximation calculations, not the deterministic
ODE or a new full-game Nash solver. Numerical residuals are not interval certified.
"""
import math
import time

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, bicgstab, gmres, spsolve

from .hjb import build_generator, own_hamiltonian, piecewise_best_response
from .primitives import payoffs


def _vector(value, count, name, bounded=False):
    a = np.asarray(value, dtype=float).ravel()
    if len(a) != count or not np.isfinite(a).all() or (bounded and np.any((a < 0) | (a > 1))):
        raise ValueError(f"Invalid finite {name} vector")
    return a.copy()


def _actions(player, own, opponent):
    return (own, opponent) if player == 0 else (opponent, own)


def _greedy(grid, p, player, value, own, opponent):
    axis = 2 if player == 0 else 3
    pipeline = grid.states[:, axis]
    minus, plus = grid.derivative_pair(value, axis)
    base = (p.a_u * (1 - grid.states[:, 0]) if player == 0 else p.a_c * (1 - grid.states[:, 1]))
    cost, coupling, kappa = ((p.k_u, p.q_u, p.kappa_c) if player == 0 else (p.k_c, p.q_c, p.kappa_u))
    best, score = piecewise_best_response(opponent, pipeline, base, cost, coupling, kappa, minus, plus)
    current = own_hamiltonian(own, opponent, pipeline, base, cost, coupling, kappa, minus, plus)
    return best, np.maximum(0., score - current)


def evaluate_fixed_player(grid, p, player, own, opponent, initial=None, linear_rtol=1e-12, direct=False):
    """Solve one player's fixed-policy linear equation; opponent is never updated."""
    if player not in {0, 1} or not math.isfinite(linear_rtol) or linear_rtol <= 0:
        raise ValueError("Player must be 0/1 and linear tolerance positive")
    own = _vector(own, grid.count, 'own policy', bounded=True)
    opponent = _vector(opponent, grid.count, 'opponent policy', bounded=True)
    rho = p.rho_u if player == 0 else p.rho_c
    u, c = _actions(player, own, opponent)
    generator = build_generator(grid, p, u, c)
    reward = np.asarray(payoffs(grid.states, u, c, p)[player])
    matrix = rho * sparse.eye(grid.count, format='csr') - generator
    iterations = [0]
    def callback(_):
        iterations[0] += 1
    if direct:
        value = spsolve(matrix, reward)
        method = 'spsolve'; code = 0
    else:
        preconditioner = LinearOperator(matrix.shape, matvec=lambda x: x / matrix.diagonal())
        initial = None if initial is None else _vector(initial, grid.count, 'initial value')
        value, code = bicgstab(matrix, reward, x0=initial, M=preconditioner,
                               rtol=linear_rtol, atol=1e-14, maxiter=3000, callback=callback)
        method = 'bicgstab_jacobi'
        if code != 0 or not np.isfinite(value).all():
            value, code = gmres(matrix, reward, x0=value if np.isfinite(value).all() else None,
                                M=preconditioner, rtol=linear_rtol, atol=1e-14,
                                restart=100, maxiter=300, callback=callback, callback_type='legacy')
            method = 'gmres_jacobi_fallback'
    residual = rho * value - reward - generator @ value
    if code != 0 or not np.isfinite(value).all():
        raise RuntimeError(f"One-player policy evaluation failed: {code}")
    return value, dict(linear_method=method, iterations=iterations[0],
                       policy_residual_inf=float(np.max(abs(residual))),
                       reward_inf=float(np.max(abs(reward))), generator_nnz=int(generator.nnz))


def solve_fixed_opponent_mdp(grid, p, player, own, opponent, initial=None,
                             max_iterations=100, gap_tolerance=1e-11,
                             linear_rtol=1e-12, direct=False, evaluation_tolerance=1e-8):
    """Howard iteration against one frozen opponent policy; no Nash implication.

    Global maximization includes both pipeline drift directions and their kink.
    The final optimality residual is reported even when the budget is exhausted.
    """
    if player not in {0, 1} or not isinstance(max_iterations, int) or max_iterations < 1 or not np.isfinite([gap_tolerance, evaluation_tolerance]).all() or min(gap_tolerance, evaluation_tolerance) <= 0:
        raise ValueError('Valid player, integer iteration budget and positive gap tolerance required')
    own = _vector(own, grid.count, 'own policy', bounded=True)
    opponent = _vector(opponent, grid.count, 'opponent policy', bounded=True)
    began = time.perf_counter(); history = []; value = initial
    for iteration in range(max_iterations):
        value, evaluation = evaluate_fixed_player(grid, p, player, own, opponent, value, linear_rtol, direct)
        best, gap = _greedy(grid, p, player, value, own, opponent)
        maximum = float(gap.max())
        history.append(dict(iteration=iteration, global_hamiltonian_gain=maximum,
                            best_response_action_difference=float(np.max(abs(best - own))), **evaluation))
        evaluation_pass = evaluation['policy_residual_inf'] <= evaluation_tolerance * (1 + evaluation['reward_inf'])
        if maximum <= gap_tolerance and evaluation_pass:
            break
        if iteration + 1 < max_iterations:
            own = best
    # Value and own policy correspond even at a failed iteration budget.
    return dict(player=player, own=own, value=value, fixed_opponent=opponent,
                solved_own_mdp=maximum <= gap_tolerance and evaluation_pass,
                policy_evaluation_scaled_tolerance=evaluation_tolerance,
                policy_evaluation_pass=bool(evaluation_pass),
                optimality_gap_inf=maximum, evaluation=evaluation,
                history=history, elapsed_seconds=time.perf_counter() - began,
                strategy_concept='unilateral_stationary_feedback_best_response_to_fixed_opponent_on_finite_state_CTMC',
                full_game_nash_verified=False, continuous_mpe_certified=False,
                floating_point_interval_certified=False)


def discounted_regret_enclosure(base_value, base_residual_inf, base_gap_inf,
                                 deviation_value, deviation_residual_inf,
                                 deviation_gap_inf, rho):
    """Residual-based exact-arithmetic bounds evaluated using floating-point inputs.

    E=||rho*V-r_pi-L_pi*V|| gives ||V-V_pi||<=E/rho. If G is
    the maximal global Hamiltonian gain, V* - V_pi <= (G+2E)/rho.
    W for an explicit deviation policy mu supplies the lower bound, and its
    residual and global gain refine the upper bound. Standard numerical inputs
    do not turn these exact mathematical inequalities into interval arithmetic.
    """
    base = np.asarray(base_value, dtype=float)
    deviation = np.asarray(deviation_value, dtype=float)
    inputs = [base_residual_inf, base_gap_inf, deviation_residual_inf, deviation_gap_inf]
    if base.shape != deviation.shape or not base.size or not np.isfinite(base).all() or not np.isfinite(deviation).all() or not np.isfinite(inputs + [rho]).all() or min(inputs) < 0 or rho <= 0:
        raise ValueError('Compatible finite values, nonnegative residuals/gaps and positive discount required')
    coarse = (base_gap_inf + 2 * base_residual_inf) / rho
    error = (base_residual_inf + deviation_residual_inf) / rho
    difference = deviation - base
    lower = np.maximum(0., difference - error)
    upper = np.minimum(coarse, np.maximum(0., difference + error + deviation_gap_inf / rho))
    if np.any(lower > upper + 1e-8 * (1 + coarse)):
        raise ArithmeticError('Inconsistent Bellman regret bounds; inputs or numerical calculation invalid')
    return dict(lower_by_state=lower, upper_by_state=upper,
                max_optimized_policy_gain=float(difference.max()),
                residual_based_global_gain_lower_bound=float(lower.max()),
                residual_based_global_regret_upper_bound=float(upper.max()),
                baseline_global_regret_upper_bound=float(coarse),
                bound_width=float(upper.max() - lower.max()),
                exact_arithmetic_theorem=True, floating_point_interval_certified=False)
