"""Verify paired host/disconnected-container release evidence after copying it.

Run after container_extension_check.py and copying its report, run manifest,
replication JSON, JUnit XML, manuscript PDF/log and build record to the standard
container_extension_* paths. This audits a current-host container, not a second
machine, historical release-byte certification or empirical publication readiness.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from weaponized.reporting.latex import tex_diagnostics

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument("--container-name",required=True)
    args=parser.parse_args()
    os.chdir(ROOT)
    read=lambda p:json.loads(Path(p).read_text())
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    host=read("outputs/diagnostics/end_to_end_replication.json")
    container=read("outputs/diagnostics/container_extension_replication.json")
    extension=read("outputs/diagnostics/container_extension_validation.json")
    manifest=read("outputs/diagnostics/container_extension_manifest.json")["file_sha256"]
    validation=read("outputs/diagnostics/data_validation.json")
    summary=read("outputs/research_summary.json")
    build=read("outputs/diagnostics/container_extension_build.json")
    convergence=[read(p) for p in ["outputs/diagnostics/manuscript_convergence.json",
                                    "outputs/diagnostics/container_extension_manuscript_convergence.json"]]
    core=read("outputs/diagnostics/scientific_code_comparison.json")
    baseline=read("outputs/diagnostics/container_run_manifest.json")["file_sha256"]
    compared=[p for p in manifest if p.split("/")[0] in {"src","scripts","configs","codebooks","tests"} or p in {"Dockerfile","pyproject.toml","uv.lock"}]
    code_bad=[p for p in compared if sha(p)!=manifest[p]]
    artifact_bad=[r["path"] for r in extension["tables_byte_identity"] if not r["passed"] or sha(r["path"])!=manifest[r["path"]]]
    core_bad=[p for p in core["core_files"] if sha(p)!=baseline.get(p)]
    env=dict(os.environ,DOCKER_CONFIG=str(ROOT/".cache/docker"))
    inspection=json.loads(subprocess.check_output(["docker","inspect",args.container_name],env=env))[0]
    pdfs=["manuscript/main.pdf","outputs/diagnostics/container_extension_manuscript.pdf"]
    texts=[" ".join(subprocess.check_output(["pdftotext","-layout",p,"-"],text=True).split()) for p in pdfs]
    pages=[int(re.search(r"^Pages:\s+(\d+)",subprocess.check_output(["pdfinfo",p],text=True),re.M)[1]) for p in pdfs]
    logs="\n".join(Path(p).read_text() for p in ["outputs/diagnostics/manuscript_build.log","outputs/diagnostics/container_extension_manuscript_build.log"])
    whitespace=subprocess.run(["git","diff","--check","HEAD","--","*.py","*.md","*.tex","*.bib","*.json","*.csv"],capture_output=True,text=True)
    junit=ET.parse("outputs/diagnostics/pytest.xml").getroot()
    suites=[junit] if junit.tag=="testsuite" else list(junit.iter("testsuite"))
    tests={k:sum(int(s.get(k,0)) for s in suites) for k in ["tests","failures","errors","skipped"]}
    checks=dict(host_pipeline=host["passed"],container_pipeline=container["passed"],container_extension=extension["passed"],
                test_suite_matches_host=extension["test_results"]=={k:summary[k] for k in ["tests","test_failures"]},
                actual_tests_executed=tests["tests"]>0 and tests["tests"]==summary["tests"] and tests["failures"]+tests["errors"]==0,
                container_data_validation_matches_host=manifest["outputs/diagnostics/data_validation.json"]==sha("outputs/diagnostics/data_validation.json"),
                all_compared_artifacts_identical=not artifact_bad,provenance=validation["passed"],
                source_tests_scripts_configs_codebooks_match_container=not code_bad,
                numerical_core_matches_original_full_run=not core_bad,
                manuscript_source_matches_container=sha("manuscript/main.tex")==manifest["manuscript/main.tex"],
                manuscript_extracted_text_identical=texts[0]==texts[1],
                container_network_none=inspection["HostConfig"]["NetworkMode"]=="none",
                container_exit_zero=inspection["State"]["ExitCode"]==0 and not inspection["State"]["Running"],
                container_image_matches_record=inspection["Image"]==build["image_id"],
                no_layout_errors=not tex_diagnostics(logs),
                manuscript_builds_converged=all(r["passed"] and r["auxiliary_files_stable"] for r in convergence),
                source_and_document_whitespace=whitespace.returncode==0)
    result=dict(passed=all(checks.values()),checks=checks,execution_timestamp=datetime.now(timezone.utc).isoformat(),freeze="2026-10-11",
                tests=tests,provenance_checks=validation["checked_claims_and_artifacts"],compared_artifacts=len(extension["tables_byte_identity"]),
                code_and_configuration_files_compared=len(compared),test_files_included=True,
                code_mismatches=code_bad,artifact_mismatches=artifact_bad,core_mismatches=core_bad,
                manuscript_pages=pages[0],container_manuscript_pages=pages[1],
                manuscript_extracted_text_identical=texts[0]==texts[1],
                host_container_manuscript_bytes_identical=sha(pdfs[0])==sha(pdfs[1]),manuscript_pdf_byte_identity_required=False,
                container_seconds=container["total_seconds"],independent_machine=False,large_hjb_recomputed=False,
                original_at_vintage_source_bytes_independently_certified=False,publication_ready=False,
                remaining_requirements="audit/remaining_requirements.md",
                original_quote_checks=summary["original_quote_checks"],mp_native_cell_versions=summary["mp_native_cell_versions"],
                mp_definition_claims=summary["mp_definition_claims"],mp_baseline_origin_metric_pairs=summary["mp_baseline_origin_metric_pairs"])
    result["smic_operating_observations"]=summary["smic_operating_observations"]
    result["smic_operating_quarters"]=summary["smic_operating_quarters"]
    result["smic_operating_definitions"]=summary["smic_definition_claims"]
    result["entity_schedule_versions"]=summary["entity_schedule_versions"]
    result["entity_schedule_rules"]=summary["entity_schedule_rules"]
    result["entity_source_rows"]=summary["entity_source_rows"]
    result["constant_commitment_scenarios"]=summary["constant_commitment_scenarios"]
    result["additional_negative_not_solved"]=summary["additional_negative_not_solved"]
    result["new_negative_hjb_runs_recomputed_on_host"]=3
    result["new_negative_hjb_runs_recomputed_in_extension_container"]=False
    result["operating_origin_claims"]=summary["operating_origin_claims"]
    result["veu_clause_checks"]=summary["veu_clause_checks"]
    result["dynamic_deviation_audits"]=summary["dynamic_deviation_audits"]
    result["safeguarded_attempts"]=summary["safeguarded_attempts"]
    result["safeguarded_fine_candidates"]=summary["safeguarded_fine_candidates"]
    result["current_safeguarded_searches_recomputed_on_host"]=summary["safeguarded_attempts"]
    result["current_safeguarded_searches_recomputed_in_extension_container"]=False
    result["dynamic_unilateral_solves_recomputed_on_both"]=summary["dynamic_deviation_audits"]
    Path("outputs/diagnostics/final_release_validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return int(not result["passed"])


if __name__ == "__main__":raise SystemExit(main())
