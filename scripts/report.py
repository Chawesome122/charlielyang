#!/usr/bin/env python3
"""Generate manuscript inputs from executed results and immutable source tables."""
import argparse
import json
import os
os.environ.setdefault("MPLCONFIGDIR","/tmp/weaponized-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME","/tmp/weaponized-cache")
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weaponized.reporting.manifest import write_manifest
from weaponized.io.archive import sha256_file

ROOT=Path(__file__).resolve().parents[1]


def figure_output(fig, name):
    folder=ROOT/"outputs/empirical/rare_earths"
    for ext in ["pdf","png"]:
        fig.savefig(folder/f"{name}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def generate_exhibits():
    frame=pd.read_csv(ROOT/"data/processed/rare_earths/observations_asof_freeze.csv")
    lynas=pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_annual_production.csv")
    yearly=frame[(frame.entity_id=="MP_MountainPass_separation")&(frame.variable=="reported_output_year")&frame.value.notna()].copy()
    yearly["year"]=pd.to_datetime(yearly.valid_date).dt.year
    ly=lynas[lynas.product_basis=="NdPr_oxide_product_family"].copy()
    ly["year"]=pd.to_datetime(ly.period_end).dt.year
    fig,axes=plt.subplots(1,2,figsize=(10,3.6))
    for ax,data,x,y,title in [(axes[0],yearly,"year","value","MP Materials: calendar-year output"),(axes[1],ly,"year","value","Lynas: fiscal years ended June")]:
        data=data.sort_values(x)
        ax.plot(data[x],data[y],"o-",color="#236a8a")
        ax.set(title=title,xlabel="Year",ylabel="Reported NdPr oxide/product-family tonnes")
        ax.grid(alpha=.2)
    fig.suptitle("Observed company-reported production; distinct native product definitions",fontsize=11)
    fig.text(.5,-.04,"No element-mass conversion, cross-company sum, magnet equivalence or China-free service inference.",ha="center",fontsize=8)
    fig.tight_layout()
    figure_output(fig,"reported_ndpr_output")
    # Diagram shows the model's required constraints, not an empirical flow solve.
    fig,ax=plt.subplots(figsize=(10,2.6));ax.set_axis_off()
    labels=["Mine / finite feed\nNd, Pr, Dy, Tb assay", "Separated oxides\nJoint recovery recipes", "Metal and alloy\nShared processing limits", "Qualified magnets\nGrade-specific demand"]
    for i,label in enumerate(labels):
        x=.12+.25*i
        ax.text(x,.58,label,ha="center",va="center",transform=ax.transAxes,bbox=dict(boxstyle="round,pad=.6",fc="#edf3f6",ec="#236a8a"),fontsize=9)
        if i<3:ax.annotate("",xy=(x+.16,.58),xytext=(x+.10,.58),xycoords="axes fraction",arrowprops=dict(arrowstyle="->",color="#236a8a"))
    ax.text(.5,.15,"Every arrow requires a valid route, ownership/origin tags and conserved material.\nEmpirical recipes, route limits and final-grade demand are incomplete.",ha="center",transform=ax.transAxes,fontsize=9)
    figure_output(fig,"stage_constraints")
    # Clear sample selection: states here are reported snapshots in a purposive roster.
    states=pd.read_csv(ROOT/"data/processed/rare_earths/project_state_evidence.csv")
    current=states[states.eligible_for_asof].sort_values(["info_public_date","event_date_upper"],na_position="first").drop_duplicates("activity_id",keep="last")
    counts=pd.crosstab(current.stage,current.state).reindex(["mine","separation","metal_alloy","magnet"],fill_value=0)
    fig,ax=plt.subplots(figsize=(7,3.7));counts.plot.bar(stacked=True,ax=ax,colormap="tab20c",rot=0)
    ax.set(title="Documented activity subset: reported states, not a population risk set",ylabel="Activities",xlabel="Production stage")
    ax.legend(title="A planned; F development; C construction; Q commissioning; O operating; X cancelled",fontsize=7,title_fontsize=7,bbox_to_anchor=(.5,-.18),loc="upper center",ncol=6)
    figure_output(fig,"documented_activity_states")
    counts.to_csv(ROOT/"outputs/empirical/rare_earths/documented_activity_state_counts.csv")


def source_registry():
    records=[]
    for line in (ROOT/"metadata/rare_earth_acquisitions.jsonl").read_text().splitlines():
        rec=json.loads(line);rec["group"]="rare_earths";records.append(rec)
    normalized={}
    for row in records:
        key=row["source_id"]
        if row["status"]=="downloaded" or key not in normalized:normalized[key]=row
    derived=json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    for sid,record in normalized.items():
        resolved=derived.get(sid,{})
        if resolved.get("public_clock_source_id"):
            record["acquisition_publication_date"]=record.get("publication_date")
            for key in ["publication_date","publication_basis","public_clock_source_id","public_clock_source_sha256"]:
                record[key]=resolved[key]
    (ROOT/"metadata/source_registry.json").write_text(json.dumps(list(normalized.values()),indent=2))
    trace=[]
    for row in pd.read_csv(ROOT/"data/processed/rare_earths/observations.csv").to_dict("records"):
        trace.append(dict(claim_id=row["record_version_id"],evidence_class=row["evidence_class"],source_id=row["source_id"],sha256=row["source_sha256"],locator=row["locator"],table="data/processed/rare_earths/observations.csv"))
    for file in ["data/processed/semiconductors/legal_claims.csv","data/processed/semiconductors/reported_financial_inputs.csv","data/processed/rare_earths_additional/lynas_annual_production.csv", "data/processed/rare_earths_additional/lynas_project_history.csv", "data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv", "data/processed/industrial_evidence/technical_claims.csv", "data/processed/industrial_evidence/project_milestones.csv", "data/processed/industrial_evidence/mp_cash_ppe_versions.csv", "data/processed/project_histories/milestone_versions.csv"]:
        data=pd.read_csv(ROOT/file)
        for i,row in enumerate(data.to_dict("records")):
            trace.append(dict(claim_id=row.get("claim_id",row.get("observation_id",row.get("record_id",f"LYNAS-{i}"))),evidence_class="empirical_reported",source_id=row["source_id"],sha256=row["source_sha256"],locator=row.get("source_locator",row.get("locator")),table=file))
    for row in pd.read_csv(ROOT/"data/processed/finance_material/observations.csv").to_dict("records"):
        trace.append(dict(claim_id=row["claim_id"],evidence_class="empirical_issuer_reported_"+row["event_kind"],source_id=row["source_id"],sha256=row["source_sha256"],locator=row["locator"],table="data/processed/finance_material/observations.csv",public_clock_source_id=row["public_clock_source_id"],public_clock_source_sha256=row["public_clock_source_sha256"]))
    pd.DataFrame(trace).to_csv(ROOT/"metadata/claims_to_sources.csv",index=False)


def summary_and_tables():
    read=lambda p:json.loads((ROOT/p).read_text())
    rare=read("outputs/empirical/rare_earths/summary.json")
    game=read("outputs/scenario/game/independent_saved_candidate_audit.json")
    semiconductor=read("outputs/empirical/semiconductors/summary.json")
    opacity=read("outputs/empirical/opacity/status.json")
    benchmark=read("outputs/scenario/game/constant_control_benchmark.json")
    tests=ET.parse(ROOT/"outputs/diagnostics/pytest.xml").getroot()
    suites=list(tests.iter("testsuite"))
    test_count=sum(int(s.attrib.get("tests",0)) for s in suites)
    failures=sum(int(s.attrib.get("failures",0))+int(s.attrib.get("errors",0)) for s in suites)
    projects=pd.read_csv(ROOT/"data/processed/rare_earths/project_state_evidence.csv")
    lynas=pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_annual_production.csv")
    financial=pd.read_csv(ROOT/"data/processed/semiconductors/reported_financial_inputs.csv")
    quarterly=pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_quarterly_production_versions.csv")
    industrial=read("outputs/diagnostics/industrial_evidence_validation.json")
    coverage=read("outputs/diagnostics/evidence_coverage_validation.json")
    batch=read("outputs/empirical/rare_earths/finite_batch_evidence.json")
    investment=read("outputs/diagnostics/mp_investment_validation.json")
    history=read("outputs/diagnostics/project_history_validation.json")
    observation=read("outputs/diagnostics/project_observation_audit.json")
    finance=read("outputs/diagnostics/finance_material_validation.json")
    clocks=read("outputs/diagnostics/publication_clock_validation.json")
    result=dict(freeze="2026-10-11",tests=test_count,test_failures=failures,
                rare_earth_versioned_observations=rare["versioned_observations"], rare_earth_latest_observations=rare["latest_observations"],
                lynas_annual_observations=len(lynas),lynas_quarterly_versions=len(quarterly),project_evidence_records=len(projects),project_count=projects.project_id.nunique(),activity_count=projects.activity_id.nunique(),
                industrial_technical_claims=industrial["technical_claims"], industrial_project_records=industrial["project_records"],
                mp_cash_ppe_versions=investment["versioned_records"], mp_cash_ppe_durations=investment["distinct_reported_durations"],
                project_history_versions=history["milestone_versions"], history_disjoint_windows=history["disjoint_reported_milestones"],
                observed_state_pairs=observation["observed_pairs"], first_exit_spells_admissible=observation["first_exit_spells_admissible"],
                finance_material_claims=finance["claims"], resolved_issuer_clocks=clocks["resolved"], unresolved_issuer_clocks=clocks["unresolved"],
                documentary_coverage=coverage["documentation_counts"],
                legal_event_rows=semiconductor["verified_legal_event_rows"],financial_input_rows=len(financial),
                valid_opacity_quarters=opacity["valid_quarters"],valid_opacity_days=opacity["valid_days"],
                finite_grid_candidate_runs=game["claimed_candidate_count"],not_solved_runs=game["not_solved_count"],
                all_saved_candidates_verified=game["all_claimed_candidates_pass"],continuous_mpe_certified=False,
                constant_control_root=benchmark["policy"], empirical_threshold_probabilities_available=False,
                causal_adaptation_effects_identified=False, publication_ready=False)
    (ROOT/"outputs/research_summary.json").write_text(json.dumps(result,indent=2))
    macros={"TestCount":test_count,"RareObs":rare["versioned_observations"],"LynasObs":len(lynas),"ProjectCount":projects.project_id.nunique(),"ActivityCount":projects.activity_id.nunique(),"LegalRows":semiconductor["verified_legal_event_rows"],"FinancialRows":len(financial),"GameCandidates":game["claimed_candidate_count"],"GameFailures":game["not_solved_count"],"BenchmarkRoot":f"{benchmark['policy']:.10f}"}
    macros.update(ProjectRecords=len(projects), PublicClockActivities=coverage["documentation_counts"]["public_clock_eligible"],
                  AnnualCapacityActivities=coverage["documentation_counts"]["annual_native_capacity_documented"],
                  BatchOxideInput=f"{batch['oxide_input_tonnes']:.1f}", BatchMagnetOutput=f"{batch['magnet_output_tonnes']:.1f}",
                  BatchAdditionalInput=f"{batch['minimum_additional_input_mass_tonnes']:.1f}", BatchProductRatio=f"{batch['magnet_to_oxide_product_mass_ratio']:.1f}")
    macros.update(MPCashVersions=investment["versioned_records"], MPCashDurations=investment["distinct_reported_durations"],
                  MPCashPrevious=f"{investment['halfyear_values_usd']['2025']/1e6:.3f}", MPCashCurrent=f"{investment['halfyear_values_usd']['2026']/1e6:.3f}")
    macros.update(HistoryVersions=history["milestone_versions"], ObservedPairs=observation["observed_pairs"],
                  RepeatPairs=observation["pair_classes"].get("same_state_reobservation",0),
                  SkippedPairs=observation["pair_classes"].get("unobserved_intermediate_states_or_definition_change",0),
                  MissingPairWindows=observation["pairs_missing_event_windows"])
    plan_ratios={r["product_basis"]:r["stockpile_only_to_expanded_ratio"] for r in finance["prospective_product_comparisons"]}
    macros.update(FinanceMaterialClaims=finance["claims"],ResolvedIssuerClocks=clocks["resolved"],
                  NdPrPlannedRatio=f"{100*plan_ratios['NdPr_oxide_family']:.1f}",DyTbPlannedRatio=f"{100*plan_ratios['DyTb_oxide_combined']:.1f}")
    (ROOT/"manuscript/results.tex").write_text("% Automatically generated by scripts/report.py\n"+"\n".join(f"\\newcommand{{\\{key}}}{{{value}}}" for key,value in macros.items())+"\n")
    rows=[]
    for run in game["runs"]:
        rows.append({k:run[k] for k in ["scenario","grid_size","start","reported_status","max_unilateral_gain","best_response_action_residual"]}|{"max_hjb_residual":max(run["hjb_residuals"])})
    pd.DataFrame(rows).to_csv(ROOT/"outputs/tables/game_diagnostics.csv",index=False)
    pd.DataFrame(game["grid_refinement"]).to_csv(ROOT/"outputs/tables/grid_refinement.csv",index=False)
    table=[r"\begin{tabular}{lrrrrl}",r"\toprule Scenario & Grid & HJB sup & Gain sup & Action error & Status \\",r"\midrule"]
    diag=pd.DataFrame(rows)
    for (scenario,size),part in diag.groupby(["scenario","grid_size"]):
        if scenario not in ["adaptation_positive","adaptation_zero","adaptation_negative"]:continue
        status="candidate" if (part.reported_status=="verified_finite_grid_candidate").all() else "not solved"
        table.append(f"{scenario.replace('adaptation_','').replace('_',' ')} & {size} & {part.max_hjb_residual.max():.2e} & {part.max_unilateral_gain.max():.2e} & {part.best_response_action_residual.max():.2e} & {status}"+r" \\")
    table += [r"\bottomrule",r"\end{tabular}"]
    (ROOT/"manuscript/game_table.tex").write_text("\n".join(table)+"\n")
    import yaml
    config=yaml.safe_load((ROOT/"configs/game.yaml").read_text())
    registry=[]
    for name,value in config["parameters"].items():
        unit="year^-1" if name.startswith(("g_","delta_","kappa_","rho_")) else "dimensionless" if name.startswith("beta_") else "normalized payoff/year"
        registry.append(dict(parameter=name,value=value,unit=unit,classification="hypothetical_scenario",empirically_identified=False,source="configs/game.yaml",uncertainty="registered alternative scenarios; no empirical confidence interval"))
    pd.DataFrame(registry).to_csv(ROOT/"metadata/parameter_registry.csv",index=False)
    claims=[dict(claim="MP NdPr oxide annual output 200/1294/2599 tonnes in calendar2023/24/25",classification="company_reported_empirical",evidence="data/processed/rare_earths/observations_asof_freeze.csv"),
            dict(claim="Lynas NdPr family 5655/6558/7260 tonnes in fiscal2024/25/26",classification="company_reported_empirical",evidence="data/processed/rare_earths_additional/lynas_annual_production.csv"),
            dict(claim="Issuer reports Texas HRE facility will no longer proceed; first Dy/Tb production is not stable qualified throughput",classification="company_reported_empirical",evidence="data/processed/rare_earths_additional/lynas_project_history.csv"),
            dict(claim="Six quarterly/annual native-product totals reconcile exactly for FY2024-2026",classification="empirical_accounting_check",evidence="data/processed/rare_earths_additional/lynas_quarterly_annual_reconciliation.csv"),
            dict(claim="Eight-origin issuer-output baseline comparisons are descriptive, not system forecasting skill",classification="empirical_descriptive_hindcast",evidence="outputs/empirical/rare_earths/lynas_quarterly_baseline_scores.csv"),
            dict(claim="Issuer reports finite1.2tonne oxide to3.0tonne magnet batch; no annual capacity or complete China-free service inferred",classification="empirical_issuer_reported_finite_batch",evidence="outputs/empirical/rare_earths/finite_batch_evidence.json"),
            dict(claim="Documentation attrition counts distinguish annual nameplates from campaign totals and missing engineering inputs",classification="empirical_archive_coverage",evidence="outputs/empirical/rare_earths/evidence_coverage_by_stage.csv"),
            dict(claim="MP first-half2026 cash PPE payments307.711millionUSD vs59.473million in2025; consolidated nominal inputs, not physical output or causal effects",classification="empirical_SEC_cashflow_input",evidence="outputs/empirical/rare_earths/mp_halfyear_cash_ppe.csv"),
            dict(claim="Forty-one additional legal originals screened; procedural notices do not create control events; complete current law remains unverified",classification="primary_legal_scope_screen",evidence="data/processed/semiconductors/legal_discovery_screening.csv"),
            dict(claim="Upton filings report different substantial-completion years and a commissioning pause; both source vintages retained without silent adjudication",classification="empirical_issuer_reported_history_versions",evidence="data/processed/project_histories/milestone_versions.csv"),
            dict(claim="Observed state pairs and disclosure inventory do not establish first-exit survival exposure or a representative hazard sample",classification="empirical_observation_protocol_audit",evidence="outputs/diagnostics/project_observation_audit.json"),
            dict(claim=f"{clocks['resolved']} issuer report clocks resolved by exact dated links; undated annual links remain unresolved",classification="primary_publication_clock_evidence",evidence="data/processed/finance_material/publication_clock_audit.csv"),
            dict(claim="Issuer cash/addition and credit-balance identities reconcile; finance categories and currencies are not physical output or causal effects",classification="empirical_reported_finance_inputs",evidence="outputs/diagnostics/finance_material_validation.json"),
            dict(claim="Eneabba stockpile-only/additional-feedstock ratios compare prospective same-product figures; not observed output, annual rates or China-free service",classification="empirical_issuer_planned_product_comparison",evidence="data/processed/finance_material/prospective_product_comparisons.csv"),
            dict(claim="SMIC investment spending is an input, not identified substitution",classification="descriptive_empirical",evidence="data/processed/semiconductors/reported_financial_inputs.csv"),
            dict(claim="Constant-control root approximately0.4655712319",classification="analytical_scenario",evidence="outputs/scenario/game/constant_control_benchmark.json"),
            dict(claim="Finite-grid candidates do not certify a continuum MPE; negative beta fine grids failed",classification="numerical_scenario",evidence="outputs/scenario/game/independent_saved_candidate_audit.json")]
    for claim in claims:claim["sha256"]=sha256_file(ROOT/claim["evidence"])
    (ROOT/"manuscript/claims.json").write_text(json.dumps(claims,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument("--manifest-only",action="store_true");args=parser.parse_args()
    os.chdir(ROOT)
    (ROOT/"outputs/tables").mkdir(parents=True,exist_ok=True)
    if not args.manifest_only:
        generate_exhibits();source_registry();print(json.dumps(summary_and_tables(),indent=2))
    write_manifest(ROOT)


if __name__=="__main__":main()
