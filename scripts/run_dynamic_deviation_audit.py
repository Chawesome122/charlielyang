"""Execute fixed-opponent unilateral MDP audits of registered saved game arrays."""
import os
for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(name, '1')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/weaponized-matplotlib')

from dataclasses import asdict
import hashlib
from io import BytesIO
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from weaponized.game.dynamic_deviation_audit import _greedy, discounted_regret_enclosure, solve_fixed_opponent_mdp
from weaponized.game.hjb import StateGrid, build_generator
from weaponized.game.primitives import GameParameters, payoffs

ROOT = Path(__file__).resolve().parents[1]


def load_registered_archive(path):
    """Bind the numerical model, dimensions and axes to the saved source hash."""
    diagnostic_bytes = path.read_bytes()
    diagnostic = json.loads(diagnostic_bytes)
    archive = ROOT / diagnostic['archive']
    snapshot = archive.read_bytes()
    digest = hashlib.sha256(snapshot).hexdigest()
    if digest != diagnostic['archive_sha256']:
        raise ValueError('Source game array checksum mismatch')
    grid = StateGrid(diagnostic['grid_size'])
    p = GameParameters(**diagnostic['parameters'])
    with np.load(BytesIO(snapshot)) as data:
        if not np.array_equal(data['axis'], grid.axes[0]):
            raise ValueError('Source game grid axis mismatch')
        arrays = [data[name].ravel().copy() for name in ['u', 'c', 'value_u', 'value_c']]
    if any(a.size != grid.count or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Invalid original game vector')
    if any(np.any((a < 0) | (a > 1)) for a in arrays[:2]):
        raise ValueError('Original policy outside state-action box')
    source = dict(diagnostic_path=str(path.relative_to(ROOT)),
                  diagnostic_sha256=hashlib.sha256(diagnostic_bytes).hexdigest(),
                  original_array_path=str(archive.relative_to(ROOT)), original_array_sha256=digest,
                  source_reported_status=diagnostic['status'])
    return diagnostic, source, grid, p, arrays


def main():
    config = yaml.safe_load((ROOT / 'configs/dynamic_deviation_audit.yaml').read_text())
    out = ROOT / config['output']; out.mkdir(parents=True, exist_ok=True)
    rows = []; sources = []; histories = []; samples = []; failed_mdp = 0
    for name in config['cases']:
        diagnostic, source, grid, p, arrays = load_registered_archive(ROOT / name)
        source['case_id'] = case = f"{diagnostic['scenario']}_n{grid.size}_{diagnostic['start']}"
        sources.append(source)
        u, c, vu, vc = arrays
        base_generator = build_generator(grid, p, u, c)
        rewards = payoffs(grid.states, u, c, p)
        for player, rho in enumerate([p.rho_u, p.rho_c]):
            own, opponent = (u, c) if player == 0 else (c, u)
            base = [vu, vc][player]
            residual = rho * base - rewards[player] - base_generator @ base
            base_error = float(np.max(abs(residual)))
            _, gap = _greedy(grid, p, player, base, own, opponent)
            result = solve_fixed_opponent_mdp(grid, p, player, own, opponent, initial=base,
                                               max_iterations=config['max_iterations'],
                                               gap_tolerance=config['gap_tolerance'],
                                               linear_rtol=config['linear_rtol'],
                                               evaluation_tolerance=config['policy_evaluation_scaled_tolerance'])
            if not np.array_equal(result['fixed_opponent'], opponent):
                raise ValueError('Opponent changed during unilateral best-response audit')
            if not result['solved_own_mdp']:
                failed_mdp += 1
            bounds = discounted_regret_enclosure(base, base_error, float(gap.max()), result['value'],
                                                 result['evaluation']['policy_residual_inf'],
                                                 result['optimality_gap_inf'], rho)
            row = dict(case_id=case, scenario=diagnostic['scenario'], grid_size=grid.size,
                       nodes=grid.count, player=player, rho=rho, source_status=diagnostic['status'],
                       source_array_sha256=source['original_array_sha256'],
                       own_mdp_solved=result['solved_own_mdp'], policy_iterations=len(result['history']),
                       baseline_policy_residual_inf=base_error, baseline_hamiltonian_gain_inf=float(gap.max()),
                       optimized_policy_residual_inf=result['evaluation']['policy_residual_inf'],
                       optimized_hamiltonian_gain_inf=result['optimality_gap_inf'],
                       own_policy_change_sup=float(np.max(abs(result['own'] - own))),
                       **{k: bounds[k] for k in ['max_optimized_policy_gain', 'residual_based_global_gain_lower_bound',
                                                  'residual_based_global_regret_upper_bound',
                                                  'baseline_global_regret_upper_bound', 'bound_width']},
                       opponent_exactly_fixed=True, floating_point_interval_certified=False,
                       continuous_mpe_certified=False, empirically_calibrated=False)
            rows.append(row)
            archive = out / f'{case}_player{player}.npz'
            np.savez_compressed(archive, axis=grid.axes[0], baseline_own=own,
                                fixed_opponent=opponent, baseline_value=base,
                                optimized_own=result['own'], optimized_value=result['value'],
                                lower_regret=bounds['lower_by_state'], upper_regret=bounds['upper_by_state'])
            payload = dict(summary=row, parameters=asdict(p), source=source,
                           saved_arrays=str(archive.relative_to(ROOT)),
                           saved_arrays_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                           history=result['history'], elapsed_seconds=result['elapsed_seconds'],
                           qualification='Exact-arithmetic finite-state inequalities applied to ordinary floating-point residuals; no interval or continuum certificate')
            (out / f'{case}_player{player}.json').write_text(json.dumps(payload, indent=2) + '\n')
            histories.extend(dict(case_id=case, player=player, **h) for h in result['history'])
            for label, index in [('max_lower', int(np.argmax(bounds['lower_by_state']))),
                                 ('max_upper', int(np.argmax(bounds['upper_by_state'])))]:
                samples.append(dict(case_id=case, player=player, diagnostic=label,
                                    **dict(zip(['x', 'y', 'm', 'n'], grid.states[index])),
                                    original_own_action=own[index], deviation_own_action=result['own'][index],
                                    fixed_opponent=opponent[index], value_difference=result['value'][index] - base[index],
                                    lower_regret=bounds['lower_by_state'][index],
                                    upper_regret=bounds['upper_by_state'][index],
                                    unweighted_grid_node_not_empirical_state=True))
            print(f"{case} player{player}: solved={result['solved_own_mdp']}, "
                  f"regret=[{row['residual_based_global_gain_lower_bound']:.6g}, "
                  f"{row['residual_based_global_regret_upper_bound']:.6g}], "
                  f"iterations={len(result['history'])}", flush=True)
    table = pd.DataFrame(rows)
    for name, data in [('value_bounds', table), ('source_archives', pd.DataFrame(sources)),
                       ('policy_iteration_history', pd.DataFrame(histories)),
                       ('diagnostic_states', pd.DataFrame(samples))]:
        data.to_csv(out / f'{name}.csv', index=False)
    if not (table.residual_based_global_regret_upper_bound + 1e-8 >= table.residual_based_global_gain_lower_bound).all():
        raise ValueError('Inconsistent dynamic regret interval')
    result = dict(passed=True, classification=config['classification'], concept=config['concept'],
                  source_array_checks=len(sources), unilateral_policy_audits=len(table),
                  fixed_opponent_checks=len(table), finite_state_bound_checks=len(table),
                  converged_unilateral_mdp_solves=int(table.own_mdp_solved.sum()),
                  not_solved_unilateral_mdp_attempts=failed_mdp,
                  original_game_model_changed=False, original_game_acceptance_thresholds_changed=False,
                  full_game_nash_promoted_by_this_audit=False, continuous_mpe_certified=False,
                  floating_point_interval_certified=False, empirical_calibration=False,
                  uncertainty_is_empirical_confidence_interval=False,
                  source_label_scope='Archives retain their original accepted/not-solved game labels; this only audits individual dynamic deviations against fixed opponents')
    (out / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)
    for ax, player in zip(axes, [0, 1]):
        part = table[table.player.eq(player)].reset_index(drop=True)
        labels = part.case_id.str.replace('adaptation_', '', regex=False).str.replace('_', ' ', regex=False)
        ax.plot(np.arange(len(part)), np.maximum(part.baseline_global_regret_upper_bound, 1e-16), 'x', label='Baseline residual/gap upper bound')
        ax.vlines(np.arange(len(part)), np.maximum(part.residual_based_global_gain_lower_bound, 1e-16),
                  np.maximum(part.residual_based_global_regret_upper_bound, 1e-16), color='#246a87', lw=3,
                  label='Explicit deviation / refined upper bound')
        ax.scatter(np.arange(len(part)), np.maximum(part.residual_based_global_regret_upper_bound, 1e-16),
                   color='#246a87', s=24, zorder=3)
        ax.set(xticks=np.arange(len(part)), xticklabels=labels, yscale='log',
               ylabel='Finite-state discounted utility gain', title='U.S. unilateral MDP' if player == 0 else 'China unilateral MDP')
        ax.tick_params(axis='x', rotation=25, labelsize=8); ax.grid(axis='y', alpha=.2); ax.legend(fontsize=7)
    fig.suptitle('Hypothetical fixed-opponent dynamic deviations; ordinary floating-point bounds', fontsize=10)
    fig.text(.5, -.01, 'Maxima over model grid states; zero lower endpoints displayed at 1e-16', ha='center', fontsize=7)
    fig.tight_layout()
    for extension in ['pdf', 'png']:
        fig.savefig(out / f'value_bounds.{extension}', dpi=220, bbox_inches='tight')
    plt.close(fig)
    lines = [r'\begin{tabular}{llrrr}\toprule', r'Archive & Player & Iterations & Lower gain & Upper regret \\\midrule']
    for row in rows:
        label = row['case_id'].replace('adaptation_', '').replace('_', ' ')
        lines.append(f"{label} & {'U.S.' if row['player'] == 0 else 'China'} & {row['policy_iterations']} & "
                     f"{row['residual_based_global_gain_lower_bound']:.2g} & {row['residual_based_global_regret_upper_bound']:.2g}" + r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    # Owned output directory, leaving shared manuscript assembly to parent agent.
    (out / 'table.tex').write_text('\n'.join(lines) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
