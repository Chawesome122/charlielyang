"""Require stable TeX auxiliary files and resolved final-build diagnostics."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def tex_diagnostics(log: str) -> list[str]:
    """Inspect the final TeX log, including warnings wrapped across lines."""
    text = " ".join(log.split())
    patterns = {
        "unresolved_references": r"undefined references|Label\(s\) may have changed|Rerun to get cross-references right",
        "unresolved_citations": r"undefined citations|Citation.*?undefined|Citation\(s\) may have changed",
        "rerun_required": r"Please.*?rerun|Rerun.*?outlines|rerunfilecheck Warning",
        "layout_overflow": r"Overfull",
        "tex_error": r"LaTeX Error|Fatal error|Emergency stop",
    }
    return [name for name, pattern in patterns.items() if re.search(pattern, text, re.I)]


def build_manuscript(root: Path, max_settling_passes: int = 6) -> dict:
    """Let latexmk handle bibliography dependencies, then verify convergence.

    A successful latexmk exit alone has admitted stale TOC page numbers on a
    clean TeX Live 2022 build. Force actual final passes until the auxiliary
    files consumed and produced by a pass agree and the final log is resolved.
    No page-number normalization or warning suppression is used.
    """
    directory = root / "manuscript"
    diagnostics = root / "outputs/diagnostics"
    logpath = diagnostics / "replication_logs/manuscript.log"
    logpath.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.mkdir(parents=True, exist_ok=True)
    aux_names = ["main.aux", "main.toc", "main.out", "main.bbl"]

    def state():
        return {name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
                if (directory/name).exists() else None for name in aux_names}

    passes = []
    with logpath.open("w") as log:
        command = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
        result = subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        passes.append(dict(command=command, exit_code=result.returncode, phase="dependency_build"))
        converged = False
        if result.returncode == 0:
            for _ in range(max_settling_passes):
                before = state()
                command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-recorder", "main.tex"]
                result = subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
                after = state()
                issues = tex_diagnostics((directory/"main.log").read_text(errors="replace"))
                stable = before == after
                passes.append(dict(command=command, exit_code=result.returncode,
                                   phase="convergence_verification", stable_auxiliary_files=stable,
                                   before_sha256=before, after_sha256=after, final_log_issues=issues))
                if result.returncode:
                    break
                if stable and not issues:
                    converged = True
                    break
    if (directory/"main.log").exists():
        shutil.copyfile(directory/"main.log", diagnostics/"manuscript_build.log")
    report = dict(passed=result.returncode == 0 and converged,
                  auxiliary_files_stable=converged, passes=passes,
                  max_settling_passes=max_settling_passes,
                  note="Dependency build plus actual final TeX passes; no ignored diagnostics or normalized TOC.")
    (diagnostics/"manuscript_convergence.json").write_text(json.dumps(report, indent=2)+"\n")
    return report
