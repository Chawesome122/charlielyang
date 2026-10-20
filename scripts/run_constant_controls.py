"""Execute validated reciprocal constant-commitment benchmarks and scenarios."""
from dataclasses import asdict
import json
import os
from pathlib import Path
for key in ["OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"]:os.environ.setdefault(key,"1")
os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from weaponized.game.active_set import solve_stage_nash
from weaponized.game.constant_controls import constant_path_payoffs,private_constant_objectives,solve_constant_path_nash
from weaponized.game.primitives import GameParameters

ROOT=Path(__file__).resolve().parents[1]


def main():
    config=yaml.safe_load((ROOT/'configs/constant_controls.yaml').read_text())
    base=yaml.safe_load((ROOT/config['base_config']).read_text())
    out=ROOT/'outputs/scenario/constant_controls';out.mkdir(parents=True,exist_ok=True)
    summaries=[];runs=[];profiles=[];validations=[];crosschecks=[]
    tolerance=config['validation_tolerance'];state0=config['initial_state']
    for scenario in config['scenarios']:
        p=GameParameters(**base['parameters']).with_updates(**base['scenarios'][scenario])
        horizon=config['discount_exponents_integrated']/min(p.rho_u,p.rho_c)
        solution=solve_constant_path_nash(p,state0,starts=tuple(config['initial_china_actions']),horizon=horizon,action_tolerance=config['action_tolerance'])
        result=solution['runs'][0];u,c=result['u'],result['c']
        private=private_constant_objectives(p,state0,horizon,config['integration_rtol'],config['integration_atol'])
        refined=private_constant_objectives(p,state0,horizon,config['refinement_rtol'],config['refinement_atol'])
        full=constant_path_payoffs(p,state0,u,c,horizon,config['integration_rtol'],config['integration_atol'])
        full_refined=constant_path_payoffs(p,state0,u,c,horizon,config['refinement_rtol'],config['refinement_atol'])
        myopic=solve_stage_nash(p.a_u*(1-state0[0]),p.a_c*(1-state0[1]),p.k_u,p.k_c,p.q_u,p.q_c)[0]
        gradient_errors=[];gradient_refinements=[];max_gains=[];curvature_pass=[]
        for player,(action,other) in enumerate([(u,c),(c,u)]):
            current=private(player,action,other);tight=refined(player,action,other)
            grad=tight['first']
            kkt=max(0.,grad) if action==0 else max(0.,-grad) if action==1 else abs(grad)
            gradient_errors.append(kkt);gradient_refinements.append(abs(current['first']-grad))
            gains=[];curvatures=[]
            offset=full['values'][player]-current['value']
            for deviation in np.linspace(0,1,config['deviation_mesh']):
                value=private(player,float(deviation),other)
                gain=value['value']-current['value'];gains.append(gain);curvatures.append(value['second'])
                profiles.append(dict(scenario=scenario,player=player,constant_own_control=deviation,
                                     fixed_opponent_constant=other,candidate_own_control=action,
                                     reconstructed_original_game_payoff=value['value']+offset,
                                     gain_relative_to_candidate=gain,scope='constant-path unilateral deviations only'))
            max_gains.append(max(0.,max(gains)))
            curvature_pass.append(max(curvatures)<=-solution['certificate']['players'][player]['strong_concavity_lower_bound']+tolerance)
            for deviation in [0.,.5,1.]:
                controls=[u,c];controls[player]=deviation
                actual=constant_path_payoffs(p,state0,*controls,horizon,config['refinement_rtol'],config['refinement_atol'])['values'][player]
                predicted=private(player,deviation,other)['value']+offset
                crosschecks.append(dict(scenario=scenario,player=player,deviation=deviation,
                                        absolute_full_payoff_decomposition_error=abs(actual-predicted),passed=abs(actual-predicted)<tolerance))
        zero_error=None
        if p.beta_c==0 and p.beta_u==0:
            def exact(initial,g,delta,rho):
                steady=g/(g+delta)
                return (1-steady)/rho+(steady-initial)/(rho+g+delta)
            mu=p.rho_u*p.a_u*exact(state0[0],p.g_c,p.delta_c,p.rho_u)
            mc=p.rho_c*p.a_c*exact(state0[1],p.g_u,p.delta_u,p.rho_c)
            exact_action=solve_stage_nash(mu,mc,p.k_u,p.k_c,p.q_u,p.q_c)[0]
            zero_error=max(abs(u-exact_action.u),abs(c-exact_action.c))
        value_refinement=max(abs(np.array(full['values'])-np.array(full_refined['values'])))
        row=dict(scenario=scenario,beta_c=p.beta_c,beta_u=p.beta_u,rho_u=p.rho_u,rho_c=p.rho_c,
                 u=u,c=c,myopic_u=myopic.u,myopic_c=myopic.c,discounted_payoff_us=full['values'][0],discounted_payoff_china=full['values'][1],
                 concavity_margin_us=solution['certificate']['players'][0]['strong_concavity_lower_bound'],
                 concavity_margin_china=solution['certificate']['players'][1]['strong_concavity_lower_bound'],
                 br_composition_contraction_bound=solution['certificate']['br_composition_contraction_bound'],
                 multiple_start_action_spread=solution['multiple_start_action_spread'],
                 max_best_response_action_residual=max(r['best_response_action_residual'] for r in solution['runs']),
                 max_refined_gradient_kkt_error=max(gradient_errors),max_gradient_refinement_difference=max(gradient_refinements),
                 max_mesh_deviation_gain=max(max_gains),full_payoff_refinement_difference=value_refinement,
                 max_full_payoff_tail_bound=max(full['tail_absolute_bounds']),horizon_years=horizon,
                 exact_zero_beta_action_error=zero_error,full_feedback_mpe_certified=False,empirical=False)
        passed=all(curvature_pass) and max(gradient_errors)<tolerance and max(gradient_refinements)<tolerance and max(max_gains)<tolerance and value_refinement<tolerance and max(full['tail_absolute_bounds'])<tolerance and solution['multiple_start_action_spread']<tolerance and row['max_best_response_action_residual']<tolerance and (zero_error is None or zero_error<tolerance)
        summaries.append(row);validations.append(dict(scenario=scenario,passed=bool(passed),numerical_ODE_interval_certified=False))
        runs.extend(dict(scenario=scenario,**r) for r in solution['runs'])
        (out/f'{scenario}.json').write_text(json.dumps(dict(parameters=asdict(p),initial_state=state0,solution=solution,payoff=full,validation=validations[-1]),indent=2)+'\n')
        print(f"{scenario}: u={u:.8f}, c={c:.8f}, passed={passed}",flush=True)
        if not passed:raise ValueError('Restricted constant-path benchmark validation failed')
    summary=pd.DataFrame(summaries);profile=pd.DataFrame(profiles)
    for name,data in [('equilibria',summary),('initializations',pd.DataFrame(runs)),('unilateral_deviations',profile),('validation',pd.DataFrame(validations)),('full_payoff_crosschecks',pd.DataFrame(crosschecks))]:data.to_csv(out/f'{name}.csv',index=False)
    if not all(r['passed'] for r in crosschecks):raise ValueError('Private/full original payoff mismatch')
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.4),sharey=True)
    short=['negative beta','zero beta','positive beta','patient','impatient','substitution','complementarity','growth support','licensing input']
    for ax,player,field,myopic in zip(axes,[0,1],['u','c'],['myopic_u','myopic_c']):
        ax.bar(np.arange(len(summary)),summary[field],color='#236a8a' if player==0 else '#c06427',label='Constant-commitment Nash')
        ax.scatter(np.arange(len(summary)),summary[myopic],color='black',marker='x',label='Initial-state myopic Nash')
        ax.set(xticks=np.arange(len(summary)),xticklabels=short,ylim=(0,1),title='U.S. control u' if player==0 else 'Chinese control c')
        ax.tick_params(axis='x',rotation=60,labelsize=8);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=7)
    axes[0].set_ylabel('Hypothetical constant restriction intensity')
    fig.suptitle('Restricted reciprocal commitment game; no feedback-equilibrium or empirical policy claim',fontsize=10)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(out/f'scenario_controls.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9.8,3.8))
    for ax,player in zip(axes,[0,1]):
        for scenario in config['scenarios'][:3]:
            part=profile[profile.scenario.eq(scenario)&profile.player.eq(player)]
            ax.plot(part.constant_own_control,part.reconstructed_original_game_payoff,label=scenario.replace('adaptation_','beta '))
        ax.set(xlabel='Unilateral constant control',ylabel='Normalized discounted scenario payoff',title='U.S. commitment payoff' if player==0 else 'Chinese commitment payoff');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(out/f'commitment_payoffs.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    lines=[r'\begin{tabular}{lrrrr}\toprule',r'Scenario & $u$ & $c$ & $\mu_U$ & $L_UL_C$ \\\midrule']
    for row in summaries:lines.append(f"{row['scenario'].replace('_',' ')} & {row['u']:.4f} & {row['c']:.4f} & {row['concavity_margin_us']:.3f} & {row['br_composition_contraction_bound']:.3f}"+r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    (ROOT/'manuscript/constant_controls_table.tex').write_text('\n'.join(lines)+'\n')
    result=dict(passed=all(r['passed'] for r in validations+crosschecks),classification=config['classification'],
                concept=config['concept'],certificate_checks=len(summary),start_checks=len(runs),
                deviation_profile_points=len(profile),exact_zero_beta_checks=int(summary.exact_zero_beta_action_error.notna().sum()),
                full_payoff_crosschecks=len(crosschecks),quadrature_refinement_checks=2*len(summary),
                max_multiple_start_spread=float(summary.multiple_start_action_spread.max()),
                max_refined_gradient_kkt_error=float(summary.max_refined_gradient_kkt_error.max()),
                max_full_payoff_decomposition_error=max(r['absolute_full_payoff_decomposition_error'] for r in crosschecks),
                max_infinite_tail_bound=float(summary.max_full_payoff_tail_bound.max()),
                constant_path_equilibrium_uniqueness_sufficient_bounds_passed=True,
                numerical_ODE_interval_certified=False,full_feedback_mpe_certified=False,
                unrestricted_open_loop_equilibrium_certified=False,empirical_calibration=False)
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
