"""Regression: a zero-exit build must not admit the observed stale TOC warning."""
import pytest

from weaponized.reporting.latex import tex_diagnostics


@pytest.mark.parametrize(("log", "expected"), [
    ("Output written on main.pdf (37 pages).", []),
    ("LaTeX Warning: Label(s) may have changed. Rerun to get cross-\nreferences right.", ["unresolved_references"]),
    ("Package natbib Warning: Citation `source' on page 9\n undefined.", ["unresolved_citations"]),
    ("Package natbib Warning: There were undefined citations.", ["unresolved_citations"]),
    ("Package rerunfilecheck Warning: File `main.out' has changed.", ["rerun_required"]),
    ("Overfull \\hbox (2.0pt too wide)", ["layout_overflow"]),
    ("! LaTeX Error: File not found.", ["tex_error"]),
])
def test_unresolved_final_log_is_rejected(log, expected):
    assert tex_diagnostics(log) == expected
