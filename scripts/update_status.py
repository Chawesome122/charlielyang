"""Refresh the resumable research ledger from executed machine-readable evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    execution_date=datetime.now(timezone.utc).date().isoformat()
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
    def update(key,status,paths,evidence,remaining,expected_requirement=None):
        mask=audit.requirement_id.eq(key)
        if mask.sum() != 1 or (expected_requirement is not None and audit.loc[mask,"requirement"].iloc[0] != expected_requirement):
            raise ValueError(f"Audit identifier/requirement mismatch:{key}")
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
    update("C04","PARTIAL","data/processed/rare_earths/project_state_evidence.csv;data/processed/industrial_evidence/project_milestones.csv;outputs/diagnostics/evidence_coverage_validation.json",
           f"{summary['project_evidence_records']} source-checked records across {summary['project_count']} projects/{summary['activity_count']} activities. Includes unsuccessful histories and additional downstream disclosures; counterparty roles, target/operation distinctions and two-clock histories retained.",
           "Discovery roster is nonrepresentative. Complete historical eligibility/cohort, original state entries/exits, ownership dependence and independent qualification remain unresolved; no empirical hazards fitted.")
    update("C05","PARTIAL","src/weaponized/rare_earths/history.py;data/processed/project_histories;outputs/diagnostics/project_observation_audit.json;tests/test_history_observations.py",
           f"{summary['project_history_versions']} source-checked history versions preserve changed targets, disjoint completion windows and undated commissioning pause. {summary['observed_state_pairs']} state pairs audited; {summary['first_exit_spells_admissible']} first-exit spells admitted. Quarterly source-disclosure inventory preserves missing physical survival counts and partial freeze quarter.",
           "Representative entry cohort, verified risk spells, first-exit surveillance, reporting-delay mechanism, interval/event-definition adjudication and independent coding remain missing.",
           expected_requirement="Right/interval censoring and delayed public reporting")
    update("C01","PARTIAL","src/weaponized/rare_earths/materials.py;data/processed/finance_material;data/processed/engineering_inputs;outputs/diagnostics/engineering_inputs_validation.json",
           "32 source claims retain joint REO/concentrate denominators and separate resource/reserve assumptions; four partial grouped-oxide constraints and twelve normalized finite-feed LP checks executed. Native product and temporal bases preserved. Combined DyTb not split; reserve TREO grade not NdPr grade; prospective product figures not annualised from an implicit denominator. USD signed cash/PPE amounts, AUD book additions/credit/commitments and conditional contract revenue remain distinct.",
           "Element assays, grade-specific recipes, yields, independent throughput, complete material origins and expert confirmation of implicit prospective quantity bases remain missing.",
           expected_requirement="Element identities Nd/Pr/Dy/Tb and native forms/units preserved")
    update("14-21","PARTIAL","data/processed/finance_material;data/processed/publication_extension;data/processed/source_integrity;outputs/diagnostics/original_quote_validation.json;metadata/claims_to_sources.csv",
           f"Finite-batch/grade/source checks retained. {summary['resolved_issuer_clocks']} exact-link issuer clocks resolved; {summary['unresolved_issuer_clocks']} undated annual links remain unresolved. {summary['finance_material_claims']} claims separate cash, book additions, commitments, credit, reserve attributes and prospective feed-dependent products; two-source report/clock traceability and accounting identities executed. Fresh-original snapshot and PDF page checks executed; auxiliary dates and link aliases rejected; actual look-ahead claim counts audited.",
           "Original-at-vintage binary certification, independent engineering review, complete issuer/failure discovery and four remaining annual-report public clocks remain unresolved. No undrawn credit, reserves, targets or observed native quantities are interpreted as qualified end-to-end service.")
    update("14-03","PARTIAL","data/processed/semiconductors/legal_events.csv;data/processed/legal_provisions;outputs/diagnostics/legal_provisions_validation.json",
           f"{summary['legal_event_rows']} reviewed phases;41additional XML originals scope-screened. Entity licenses, correcting amendment, conditional UAE authorization and retained controls distinguished; administrative comment extensions excluded from new-control events. {summary['selected_legal_provisions']} selected original clauses and {summary['structured_legal_bounds']} numerical bounds preserve strict inequalities, nine certification conditions and instruction-specific compliance clocks.",
           "Term-limited discovery and single-coder screening do not consolidate current law. Remaining item/entity crosswalk, China/Japan originals, exemptions, suspensions and independent legal review remain incomplete.",
           expected_requirement="As-of October 11, 2026 policy chronology; Chinese suspended versus active rules")
    update("14-O3","PARTIAL","outputs/empirical/rare_earths/lynas_quarterly_baseline_scores.csv;outputs/empirical/rare_earths/lynas_quarterly_baseline_predictions.csv;outputs/empirical/rare_earths/baseline_scores.csv;tests/test_reported_output.py",
           "Eight publication-safe quarterly origins per Lynas product; three naive baselines; six exact annual/quarterly reconciliations. Two earlier MP annual origins retained. Historical-revision leakage test executed.",
           "Small dependent single-issuer output exercises do not establish structural forecasting skill, system-service calibration or identifiable population project hazards.")
    audit.to_csv(ROOT/"audit/blueprint_requirements.csv",index=False)
    counts=audit.status.value_counts().to_dict()
    text=f"""# Research status — resumable execution ledger

Information freeze: **2026-10-11**. Research execution date: {execution_date} (UTC). Methodological attachment:49pages. The task began from an empty, unborn Git checkout. The continuation request authorizes Git push; no journal submission has occurred.

## Implemented and executed

- Locked Python3.12 package; immutable archives/checksums; schemas; two-clock as-of selection; unit, vintage and provenance validation.
- Rare-earth primary-data extraction: **{summary['rare_earth_versioned_observations']} versioned numerical records**, {summary['rare_earth_latest_observations']} latest observations, **{summary['lynas_annual_observations']} additional Lynas annual output observations** and **{summary['lynas_quarterly_versions']} quarterly KPI versions**; {summary['project_evidence_records']} project-state records across **{summary['project_count']}projects/{summary['activity_count']}activities** in a nonexhaustive documented subset. Suspended, cancelled and delayed cases retained. Native units preserved.
- Semiconductor primary chronology: **{summary['legal_event_rows']} legal-event phases**, separately dated and classified; **{summary['financial_input_rows']} SMIC nominal investment-input observations**. These are not target-capability scores or causal effects.
- Additional industrial evidence: **{summary['industrial_project_records']} project records and {summary['industrial_technical_claims']} technical claims**. Documentation coverage: {summary['documentary_coverage']['public_clock_eligible']} source-public clocks and {summary['documentary_coverage']['annual_native_capacity_documented']} native annual capacity mentions among {summary['activity_count']} activities. No complete recipe, finite route-capacity, independent stable-rate or matched-demand evidence is verified.
- Archived SEC cash-flow inputs: **{summary['mp_cash_ppe_versions']} MP filing vintages over {summary['mp_cash_ppe_durations']} reported durations**, with six first-half observations and three exact quarter/H1 reconciliations. They are nominal consolidated cash payments, not project allocation, physical capacity or a causal restriction response.
- Project-history extension: **{summary['project_history_versions']} source-checked versions** from three RER filings; {summary['history_disjoint_windows']} disjoint reported completion window. The full roster has {summary['observed_state_pairs']} adjacent observation pairs and {summary['first_exit_spells_admissible']} admissible first-exit spells. A quarterly disclosure inventory records unknown physical survival exposure explicitly.
- Finance/material extension: **{summary['finance_material_claims']} issuer claims**, {summary['resolved_issuer_clocks']} resolved exact-link publication clocks and {summary['unresolved_issuer_clocks']} unresolved annual-report clocks. Cash/additions and facility identities checked; cash, credit, commitments, reserves and prospective product figures remain separate. Original-at-vintage web/PDF bytes are not independently certified.
- Engineering extension: **{summary['engineering_source_claims']} claims**, four conditional grouped-oxide constraints and twelve normalized finite-feed LP checks. Resource/reserve assumptions and product bases remain separate; measured operating yield, stock, Nd/Pr split, annual output and China-free service remain unknown.
- Original-source trust chain: **{summary['original_quote_checks']} quote/table checks** across nine tables and 33 originals; single immutable-byte snapshot extraction, derivative exclusion and explicit PDF page enforcement. Present archived-byte support is not historical-release certification.
- Publication extension: **{summary['rejected_auxiliary_date_candidates']} auxiliary date candidates rejected**; four annual clocks remain unknown. Actual event-date-only look-ahead counts are 15 at December 2025 and 12 at June 2026. Reports-page arrow/title link conflicts are preserved.
- Selected legal provisions: **{summary['selected_legal_provisions']} claims**, 65 operative XML elements and **{summary['structured_legal_bounds']} technical bounds** from three originals. Four parameter links do not certify full supersession/current law or numerical access.
- All 41 additional archived legal originals scope-screened; 4 documents add 5 reviewed phases. Eight procedural records do not add export requirements. Current-law consolidation and numerical access effects remain unverified.
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
- Earlier/current extension clean-container passed:{extension.get('passed',False)}. Scope:{extension.get('scope','not yet executed')}. {len(extension.get('tables_byte_identity', []))} source-derived artifacts compared byte for byte; consult its code/input hashes to distinguish the current extension from an earlier run. Large games are audited, not re-solved in this check.
- Environment setup is recorded separately from research publication. Git push is authorized; remote branch history records the actual released commit.

## Actual empirical findings

- MP reported NdPr oxide output200/1294/2599metrictonnes in2023/24/25, distinct from REO-in-concentrate or magnets.
- Lynas reported NdPr product-family5655/6558/7260tonnes in fiscal2024/25/26. Calendar/product definitions are retained, with no cross-company physical-service sum.
- Primary disclosures demonstrate project-state heterogeneity and important nonadditivity: combined expansions, mixed-output capacities, finite demonstration campaigns, shared processing and four-year offtake quantities.
- Lynas reports the Texas HRE facility will no longer proceed; its exact cancellation decision date remains unknown. Dy/Tb first production in May/June2025 and two observed Australian--Malaysian material links remain distinct from stable qualified output and complete physical feasibility.
- Energy Fuels reports approximately 1.2 tonnes NdPr oxide converted into 3.0 tonnes automotive-qualified magnets in a finite Korean-processed batch. These are issuer claims, with unknown production interval, unnamed processor and incomplete auxiliary-input origins; not annual capacity, elemental recovery or complete China-free service. Aggregate mass accounting requires approximately 1.8 tonnes or more other inputs, conditional on reported masses and nonnegative other outputs.
- SMIC's reported capex and Q4R&D vary over2022–25; no causal restriction response or successful substitution is identified.
- MP's tagged first-half cash PPE payments are USD 59.473 million in 2025 and USD 307.711 million in 2026, according to the archived SEC facts. This is an investment-input observation, not a measured gain in magnet resilience or evidence of policy causation.
- Upton's FY2024 report places substantial construction completion in late 2024; FY2025 places it in late 2025 and reports a commissioning pause/rework before demonstration operations in early 2026. Changed definitions or rework require adjudication; neither year silently overwrites the other. FY2024 pairs the planned total 10 tons with approximately 9.1 tonnes, without establishing achieved output or an annual rate.
- Pensana reports USD 15.998614 million Jul–Dec 2025 cash payments for PPE/intangibles, distinct from USD 10.998722 million additions and a USD 4.999892 million capital-working-capital adjustment. Iluka reports AUD 897.5 million drawn and AUD 752.5 million undrawn against a base AUD 1,650 million EFA facility at June 30. Credit conditions and accounting objects remain distinct from deployed project cash or physical output.
- Eneabba's prospective stockpile-only figures of 3,500 NdPr / 170 combined DyTb tonnes compare with 5,500 / 750 using additional feedstocks, subject to assemblage. Ratios are descriptive comparisons of plans, not observed service, annual rates or an Nd/Pr/Dy/Tb recipe. Iluka's notice is dated June 22; the exact issuer link is dated June 23. Take-or-pay covers 90% of the stated 1,200-tonne four-year volume, not an unconditional guaranteed physical supply or received revenue.

- Source-reported MP reserve-model Ce/La assumptions change from 11.5/75.0% in FY2024 to 8.9/74.9% in FY2025; resource assumptions do not change. The conditional PrNd-group coefficient is 0.0844974 tonne REO equivalent per native concentrate tonne, not an observed operating yield or industrial feed availability.
- Selected HBM original clauses distinguish classification density >2 from exception density <3.3 GB/s/mm² plus additional conditions. January 2026 case-by-case review retains strict TPP/bandwidth bounds and all nine certifications; no approval, physical access or domestic capability is observed.

## Failed checks and repairs preserved

- Primary-source proxy/CDN denials and challenge pages remain logged; USGS full data/PDF and China/Japan legal coverage remain incomplete.
- Current continuation attempted 8 additional rare-earth issuer sites; all failed at the proxy with CONNECT 403. Exact attempts are in`metadata/rare_earth_expansion_acquisitions.jsonl`; no source or observation is claimed from them.
- Exact Q2 2026 SEC filing requests for MP, Energy Fuels and USA Rare Earth also failed with CONNECT 403. Filing pointers/public dates come from archived submission metadata; the inaccessible texts are not treated as read. The pre-existing MP company-facts archive provides a distinct financial-data fallback.
- The additional RER Q2 2026 original also failed with CONNECT 403; `metadata/project_history_acquisitions.jsonl` preserves the exact accession URL. New history claims come from existing archived annual filings, not the inaccessible quarterly text.
- The additional Iluka half-year presentation request failed with CONNECT 403; exact URL and error are in `metadata/finance_material_acquisitions.jsonl`. New finance/material evidence comes from existing hashed reports and issuer pages. Four annual-report dates remain missing; signatures, filenames and page-modification dates are not substituted as public clocks.
- Three new official annual-release index requests also failed CONNECT 403; `metadata/publication_extension_acquisitions.jsonl` preserves exact URLs/errors. No new source download or publication date is claimed.
- Original-source review repaired editable text-aid trust, a hash/extraction path-replacement race and omitted page-locator enforcement. Snapshot-mutation and explicit-page regression checks executed; original economic observations remain unchanged.
- Incorrect attempted legacy company identifier rejected; premerger SPAC records excluded from industrial history.
- Independent review repaired inventory reuse/NaN in a stateless bridge, unauditable forecast-input vintages and false stability at nonsmooth interpolation knots.
- A real BiCGSTAB stagnation was repaired by recorded GMRES recovery without disabling verification or relaxing residual tolerances.
- Four positive fine-grid starts originally hit an80-iteration budget; original attempts preserved and budget extended to120with unchanged thresholds. Negative-beta fine-grid nonlinear failures remain unresolved.
- Initial Docker setup failed because its default config path was read-only and proxy DNS was unavailable inside Docker. Supported writable configuration, the same proxy route and the platform-provided public CA were used; TLS verification was never disabled.

## Unresolved scientific requirements

**No empirical China-free magnet-service series or2028/2031/2035probabilities; no population completion hazards; no causal semiconductor substitution effect; no coverage-valid historical SPOI; no identified national utility coefficients; no continuous pure-feedback equilibrium certificate.**

Full requirements:`audit/remaining_requirements.md`. The85-row acceptance ledger currently records:{counts}. A VERIFIED mathematical item is not empirical validation. The manuscript is **not publication-ready**.

## Exact next milestone

1.Read `docs/engineering_inputs_review.md`, `docs/legal_provisions_review.md`, `docs/publication_extension_review.md`, `docs/original_source_integrity.md` and the audit. Resolve remaining annual-report clocks and original-at-vintage evidence, obtain Q2 originals and Upton adjudication, and collect verified entry/risk clocks plus plant/route/recipe/demand inputs before estimating hazards or physical service.
2.Obtain engineering review and qualified semiconductor z/f observations; finish primary legal consolidation.
3.Establish opacity obligations and blinded independent coding before estimating project associations.
4.Fit empirical transitions/state laws only when these gates pass; continue negative-beta solver work with truthful failure labels.
5.Run`uv sync --frozen` then`uv run python scripts/replicate.py`; inspect each diagnostic and the manuscript claim manifest. Use`--full` when changing game primitives/solvers or independently recomputing the numerical release.

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
