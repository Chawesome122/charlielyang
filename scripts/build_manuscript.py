"""Build the manuscript with verified auxiliary-file and final-log convergence."""
from pathlib import Path

from weaponized.reporting.latex import build_manuscript


if __name__ == "__main__":
    report = build_manuscript(Path(__file__).resolve().parents[1])
    print({"passed": report["passed"], "passes": len(report["passes"])})
    raise SystemExit(not report["passed"])
