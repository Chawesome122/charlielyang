import importlib.metadata
import json
import platform
import subprocess
import shutil
from pathlib import Path
from weaponized.io.archive import sha256_file


def create_manifest(root: Path) -> dict:
    commit = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, capture_output=True, text=True) if shutil.which("git") else None
    roots = ["src", "scripts", "configs", "codebooks", "metadata", "data", "tests", "references", "manuscript", "outputs", "docs", "audit"]
    files = []
    for directory in roots:
        for path in sorted((root/directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name == "run_manifest.json":
                continue
            if path.suffix in {".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".blg"}:
                continue
            files.append(path)
    files += [root/f for f in ["pyproject.toml", "uv.lock", "Dockerfile", "README.md", "AGENTS.md", "PLANS.md", "RESEARCH_STATUS.md", "Makefile", "LICENSE", "CITATION.cff", "THIRD_PARTY_NOTICES.md"] if (root/f).is_file()]
    return dict(research_freeze="2026-10-11", git_commit=commit.stdout.strip() if commit is not None and commit.returncode == 0 else None,
                git_state_note="git_commit records HEAD at generation time; file digests identify the exact working files, including uncommitted changes",
                python=platform.python_version(), platform=platform.platform(),
                dependencies={name:importlib.metadata.version(name) for name in ["numpy","scipy","pandas","matplotlib","PyYAML","requests","pydantic","statsmodels","pytest"]},
                base_image="python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e",
                uv_version="0.12.23", empirical_and_synthetic_separated=True,
                file_sha256={str(path.relative_to(root)):sha256_file(path) for path in files},
                source_manifest_paths=sorted({str(p.relative_to(root)) for p in (root/"metadata").glob("*acquisitions.jsonl")} | {"metadata/additional_rare_earth_sources.csv", "metadata/semiconductor_sources.csv", "metadata/opacity_sources.csv", "metadata/literature_sources.csv", "metadata/literature_sources_additional.csv", "metadata/citation_audit.csv"}),
                publication_clock_audit="data/processed/finance_material/publication_clock_audit.csv",
                seeds={"parameters":101,"projects":202,"process_yields":303,"common_shocks":404,"graphics":505},
                limitations=["Current-host and clean-container results are not an independent second-machine replication", "No continuous-state MPE or real-world threshold probabilities are certified"])


def write_manifest(root: Path):
    path=root/"outputs/run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(create_manifest(root), indent=2, sort_keys=True)+"\n")
