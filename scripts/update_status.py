"""Refresh the resumable research ledger from executed machine-readable evidence."""
import json
from pathlib import Path
import re
import subprocess
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    summary=json.loads((ROOT/"outputs/research_summary.json").read_text())
    endpath=ROOT/"outputs/diagnostics/end_to_end_replication.json"
    end=json.loads(endpath.read_text()) if endpath.exists() else {}
    containerpath=ROOT/"outputs/diagnostics/container_validation.json"
    container=json.loads(containerpath.read_text()) if containerpath.exists() else {}
    extensionpath=ROOT/"outputs/diagnostics/container_extension_validation.json"
    extension=json.loads(extensionpath.read_text()) if extensionpath.exists() else {}
    info=subprocess.run(["pdfinfo",str(ROOT/"manuscript/main.pdf")],capture_output=True,text=True)
    match=re.search(r"^Pages:\s+(\d+)",info.stdout,re.M)
    pages=int(match[1]) if match else "unknown"
    audit=pd.read_csv(ROOT/"audit/blueprint_requirements.csv").fillna("")
    marker=" Final current-instance verification:"
    for i,row in audit.iterrows():
        old=str(row.executed_evidence).split(marker)[0]
        audit.loc[i,"executed_evidence"]=old+marker+f" {summary['tests']} tests, {summary['test_failures']} failures; outputs/diagnostics/pytest.xml."
    def update(key,status,paths,evidence,remaining):
        mask=audit.requirement_id.eq(key)
        audit.loc[mask,["status","evidence_paths","executed_evidence","remaining_requirement"]]=[status,paths,evidence,remaining]
    update("C39","VERIFIED","manuscript/main.tex;manuscript/main.pdf;manuscript/claims.json;outputs/diagnostics/manuscript_build.log",
           f"Prescribed sections and technical appendices written; {pages}-page PDF compiled. Evidence-limited draft, explicitly not publication-ready.",
           "Empirical gaps and specialist review still block publication under14-25/14-O5, rather than being fabricated in results sections.")
    update("C37","VERIFIED","outputs/run_manifest.json;metadata/claims_to_sources.csv;manuscript/claims.json;scripts/report.py",
           "Machine-readable source/config/code/output hashes and principal manuscript claim links generated from actual files.",
           "Independent-machine release verification remains C38; no self-hash is claimed.")
    full_container=container.get("passed") and container.get("scope")=="clean_container_full_recomputation"
    update("T15","VERIFIED" if full_container else "PARTIAL" if container.get("passed") else "BLOCKED",
           "Dockerfile;scripts/build_container.py;outputs/diagnostics/container_build.json;outputs/diagnostics/container_validation.json;outputs/diagnostics/end_to_end_replication.json",
           f"Current-instance replication passed={end.get('passed',False)};clean-container check passed={container.get('passed',False)};container scope={container.get('scope','not completed')}.",
           "Second independent machine remains unavailable; same-host clean-container verification is complete only when full recomputation passed.")
    if full_container:
        update("C36","VERIFIED","pyproject.toml;uv.lock;Dockerfile;scripts/build_container.py;outputs/diagnostics/container_build.json;outputs/diagnostics/container_validation.json",
               "Python3.12.14 base pulled by verified digest; uv0.12.23 installed; frozen resolved dependencies and noneditable src wheel built; full network-disabled clean-container computation and133tests passed.",
               "OS package build versions are recorded; a second independent machine remains C38, not implied by this result.")
    if end.get("passed"):
        update("14-O1","PARTIAL","scripts/replicate.py;outputs/diagnostics/end_to_end_replication.json;manuscript/main.pdf",
               f"Offline end-to-end pipeline executed successfully:scope={end.get('scope')}. It regenerates evidence, validation/scenarios, exhibits and manuscript; no missing empirical coefficient is manufactured.",
               "Full hierarchical empirical transition fit, measured x/y and complete physical/demand network still unavailable.")
    update("C04","PARTIAL","data/processed/rare_earths/project_state_evidence.csv;data/processed/rare_earths_additional/lynas_project_history.csv;outputs/diagnostics/lynas_history_validation.json",
           f"{summary['project_evidence_records']} source-checked records across {summary['project_count']} projects/{summary['activity_count']} activities. Includes Texas cancellation and retrospectively disclosed Mountain Pass cold-idle/relaunch; two-clock histories retained.",
           "Discovery roster is nonrepresentative. Complete historical eligibility/cohort, original state entries/exits, ownership dependence and independent qualification remain unresolved; no empirical hazards fitted.")
    update("14-O3","PARTIAL","outputs/empirical/rare_earths/lynas_quarterly_baseline_scores.csv;outputs/empirical/rare_earths/lynas_quarterly_baseline_predictions.csv;outputs/empirical/rare_earths/baseline_scores.csv;tests/test_reported_output.py",
           "Eight publication-safe quarterly origins per Lynas product; three naive baselines; six exact annual/quarterly reconciliations. Two earlier MP annual origins retained. Historical-revision leakage test executed.",
           "Small dependent single-issuer output exercises do not establish structural forecasting skill, system-service calibration or identifiable population project hazards.")
    audit.to_csv(ROOT/"audit/blueprint_requirements.csv",index=False)
    counts=audit.status.value_counts().to_dict()
    text=f"""# Research status — resumable execution ledger

Information freeze: **2026-10-11**. Research execution date:2026-10-18. Methodological attachment:49pages. The task began from an empty, unborn Git checkout. The continuation request authorizes Git push; no journal submission has occurred.

## Implemented and executed

- Locked Python3.12 package; immutable archives/checksums; schemas; two-clock as-of selection; unit, vintage and provenance validation.
- Rare-earth primary-data extraction: **{summary['rare_earth_versioned_observations']} versioned numerical records**, {summary['rare_earth_latest_observations']} latest observations, **{summary['lynas_annual_observations']} additional Lynas annual output observations** and **{summary['lynas_quarterly_versions']} quarterly KPI versions**; {summary['project_evidence_records']} project-state records across **{summary['project_count']}projects/{summary['activity_count']}activities** in a nonexhaustive documented subset. Suspended, cancelled and delayed cases retained. Native units preserved.
- Semiconductor primary chronology: **{summary['legal_event_rows']} legal-event phases**, separately dated and classified; **{summary['financial_input_rows']} SMIC nominal investment-input observations**. These are not target-capability scores or causal effects.
- Multi-commodity multi-quarter LP, joint products, finite feeds/resources/stocks, origin/control tags, consistent supplier N-1, primal/dual diagnostics; exact blueprint and richer synthetic fixtures executed.
- Competing-risk laws and pooled rate estimator, exact/right/interval first-exit likelihoods, ramp models, common shocks, proper scores, censor/release/persistence guards;10,000synthetic network paths and parameter-recovery experiment executed.
- Two extra MP mine-output retrospective baseline origins computed with source-vintage masks; n=2 is descriptive and does not establish forecasting skill.
- Eight publication-safe quarterly origins per Lynas product compare persistence, seasonal and available-history-mean baselines; six complete quarter/annual totals reconcile exactly. These are descriptive company-output results, not system-service forecasts.
- All ten SPOI rubrics, obligations/events, 90-day rules, daily/quarter coverage, missing/NA distinction, reliability and specification sensitivities implemented and tested. Historical index remains missing.
- Bounded ODEs, logistic folds/degeneracy, four-state payoffs/dynamics, nine constrained Nash regimes, singular continua and constant-policy root **{summary['constant_control_root']:.10f}** verified.
- Sparse4D HJB evaluation/improvement, six policy starts,17/21node refinement, global discrete unilateral tests, off-grid diagnostics and feedback stability checks executed. Latest independent archive audit: **{summary['finite_grid_candidate_runs']} accepted finite-grid runs**, **{summary['not_solved_runs']} not-solved runs**; **no continuous MPE certificate**.
- Strongest supported academic draft written and compiled: **manuscript/main.pdf ({pages} pages)**; bibliography, claims-to-source links, reproducible empirical/scenario figures and requirement audit exist.
- Latest suite: **{summary['tests']} tests passed; {summary['test_failures']} failures**. Evidence:`outputs/diagnostics/pytest.xml`.

## Replication outcome

- Current-instance end-to-end passed:{end.get('passed',False)}. Scope:{end.get('scope','not yet executed')}. Exact command exits/logs:`outputs/diagnostics/end_to_end_replication.json`.
- Earlier full clean-container passed:{container.get('passed',False)}. Scope:{container.get('scope','not yet executed')}. The continuation's additional empirical extraction is separately covered by current-instance replication and `outputs/diagnostics/container_extension_validation.json` when present. A current-host container is not an independent second machine.
- Continuation clean-container passed:{extension.get('passed',False)}. Scope:{extension.get('scope','not yet executed')}. Six source-derived tables are compared byte for byte; large games are audited, not re-solved in this extension check.
- Environment setup is recorded separately from research publication. Git push is authorized; remote branch history records the actual released commit.

## Actual empirical findings

- MP reported NdPr oxide output200/1294/2599metrictonnes in2023/24/25, distinct from REO-in-concentrate or magnets.
- Lynas reported NdPr product-family5655/6558/7260tonnes in fiscal2024/25/26. Calendar/product definitions are retained, with no cross-company physical-service sum.
- Primary disclosures demonstrate project-state heterogeneity and important nonadditivity: combined expansions, mixed-output capacities, finite demonstration campaigns, shared processing and four-year offtake quantities.
- Lynas reports the Texas HRE facility will no longer proceed; its exact cancellation decision date remains unknown. Dy/Tb first production in May/June2025 and two observed Australian--Malaysian material links remain distinct from stable qualified output and complete physical feasibility.
- SMIC's reported capex and Q4R&D vary over2022–25; no causal restriction response or successful substitution is identified.

## Failed checks and repairs preserved

- Primary-source proxy/CDN denials and challenge pages remain logged; USGS full data/PDF and China/Japan legal coverage remain incomplete.
- Incorrect attempted legacy company identifier rejected; premerger SPAC records excluded from industrial history.
- Independent review repaired inventory reuse/NaN in a stateless bridge, unauditable forecast-input vintages and false stability at nonsmooth interpolation knots.
- A real BiCGSTAB stagnation was repaired by recorded GMRES recovery without disabling verification or relaxing residual tolerances.
- Four positive fine-grid starts originally hit an80-iteration budget; original attempts preserved and budget extended to120with unchanged thresholds. Negative-beta fine-grid nonlinear failures remain unresolved.
- Initial Docker setup failed because its default config path was read-only and proxy DNS was unavailable inside Docker. Supported writable configuration, the same proxy route and the platform-provided public CA were used; TLS verification was never disabled.

## Unresolved scientific requirements

**No empirical China-free magnet-service series or2028/2031/2035probabilities; no population completion hazards; no causal semiconductor substitution effect; no coverage-valid historical SPOI; no identified national utility coefficients; no continuous pure-feedback equilibrium certificate.**

Full requirements:`audit/remaining_requirements.md`. The85-row acceptance ledger currently records:{counts}. A VERIFIED mathematical item is not empirical validation. The manuscript is **not publication-ready**.

## Exact next milestone

1.Read the audit and source-review memos; finish risk-set discovery and historically dated plant/route/recipe/demand evidence.
2.Obtain engineering review and qualified semiconductor z/f observations; finish primary legal consolidation.
3.Establish opacity obligations and blinded independent coding before estimating project associations.
4.Fit empirical transitions/state laws only when these gates pass; continue negative-beta solver work with truthful failure labels.
5.Run`uv sync --frozen` then`uv run python scripts/replicate.py --full`; inspect each diagnostic and the manuscript claim manifest.

Use the existing isolated checkout, not a new worktree. Every unfinished input stays missing rather than being replaced with a synthetic coefficient.
"""
    for old,new in {
        'date:2026':'date: 2026','attachment:49pages':'attachment: 49 pages','Python3.12':'Python 3.12',
        ';21project-state':'; 21 project-state',f"{summary['project_count']}projects/{summary['activity_count']}activities":f"{summary['project_count']} projects / {summary['activity_count']} activities",
        ';10,000synthetic':'; 10,000 synthetic','Sparse4D':'Sparse 4D',',17/21node':', 17/21 node',
        '21pages':'21 pages','0failures':'0 failures','133tests':'133 tests',
        'oxide output200/1294/2599metrictonnes in2023/24/25':'oxide output 200/1294/2599 metric tonnes in 2023/24/25',
        'product-family5655/6558/7260tonnes in fiscal2024/25/26':'product-family 5655/6558/7260 tonnes in fiscal 2024/25/26',
        'Q4R&D':'Q4 R&D','over2022–25':'over 2022–25','an80-iteration':'an 80-iteration','to120with':'to 120 with',
        'series or2028/2031/2035probabilities':'series or 2028/2031/2035 probabilities','The85-row':'The 85-row',
        '1.Read':'1. Read','2.Obtain':'2. Obtain','3.Establish':'3. Establish','4.Fit':'4. Fit','5.Run':'5. Run',
    }.items():text=text.replace(old,new)
    (ROOT/"RESEARCH_STATUS.md").write_text(text)
    (ROOT/"audit/summary.json").write_text(json.dumps(dict(requirements=len(audit),counts=counts,publication_ready=False),indent=2))
    print(json.dumps(counts,indent=2))


if __name__=="__main__":main()
