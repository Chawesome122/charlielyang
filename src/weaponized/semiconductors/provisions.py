"""Selected issued-rule clauses, never a consolidated EAR or access score."""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
import math
import operator
import re
import xml.etree.ElementTree as ET

from weaponized.semiconductors.legal import issued_xml_text


def normalize_text(node: ET.Element) -> str:
    return " ".join(" ".join(node.itertext()).split())


def verify_clause(payload: bytes, document_number: str, xpath: str, quote: str) -> str:
    """Verify one exact normalized XML element in an identified original rule.

    The locator addresses the immutable original; preamble discussion and amended
    operative text must be coded separately. No extraction-aid file is trusted.
    """
    issued_xml_text(payload, document_number)
    root = ET.fromstring(payload)
    matches = root.findall(xpath)
    if len(matches) != 1:
        raise ValueError("Clause locator must identify exactly one element")
    actual = normalize_text(matches[0])
    if actual != quote:
        raise ValueError("Exact original clause text mismatch")
    return actual


def check_clocks(publication_date, effective_date, compliance_date, freeze="2026-10-11"):
    """Validate separate issued-rule clocks without inventing advance publicity."""
    public, effect, comply, cutoff = map(date.fromisoformat,
                                      [publication_date, effective_date, compliance_date, freeze])
    if public > cutoff:
        raise ValueError("Post-freeze publication")
    if comply < effect:
        raise ValueError("Compliance cannot precede the coded legal effective date")
    # Federal Register publication can follow effect, as in the December 2024 IFR.
    return {"publication_after_effective": public > effect,
            "first_public_date_certified": False}


def issued_clause_phases(records, as_of):
    """Visible selected clauses and their issuance clocks; no repeal inference.

    Retains previous originals even after later selected restatements. Callers
    must not label this result 'law in force' without a complete amendment audit.
    """
    origin = date.fromisoformat(as_of)
    result = []
    for record in records:
        if date.fromisoformat(record["info_public_date"]) > origin:
            continue
        phase = ("announced_not_effective" if origin < date.fromisoformat(record["effective_date"])
                 else "effective_compliance_deferred" if origin < date.fromisoformat(record["compliance_date"])
                 else "issued_compliance_date_reached_not_current_law_certified")
        result.append(dict(record, issued_phase=phase))
    return result


def parameter_screen(parameters, bounds):
    """Evaluate one conjunction of quoted technical bounds, not legal eligibility.

    Unknown inputs yield unknown. Extra jurisdiction/user/authorization conditions
    are deliberately not guessed. OR branches must be screened separately.
    """
    comparators = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}
    evaluated = []
    for bound in bounds:
        if bound["operator"] not in comparators:
            raise ValueError("Unregistered threshold operator")
        threshold = float(bound["value"])
        if not math.isfinite(threshold) or threshold < 0:
            raise ValueError("Threshold must be finite and nonnegative")
        value = parameters.get(bound["variable"])
        if value is None:
            evaluated.append(None)
            continue
        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise ValueError("Parameter must be finite and nonnegative or explicitly missing")
        evaluated.append(comparators[bound["operator"]](value, threshold))
    if not evaluated:
        raise ValueError("A parameter screen needs quoted bounds")
    matched = False if False in evaluated else None if None in evaluated else True
    return {"parameter_bounds_satisfied": matched, "legal_eligibility_determined": False,
            "license_approval_determined": False, "access_or_capability_score": None}


# Registered semantic names and their source-defined measurement bases. These
# identify quantities/units, not expected threshold values: every numeric bound
# and comparison is parsed from the reviewed original quote at execution time.
_PARAMETER_NAMES = {
    "total_processing_performance": r"\btotal processing performance\b|\bTPP\b",
    "performance_density": r"\bperformance density\b",
    "memory_bandwidth_density": r"\bmemory bandwidth density\b",
    "total_dram_bandwidth": r"\btotal DRAM bandwidth\b",
}
_PARAMETER_UNITS = {
    "total_processing_performance": "TPP; 2 * MacTOPS * operation_bit_length",
    "performance_density": "TPP per square millimeter applicable logic die area",
    "memory_bandwidth_density": "GB/s/mm^2 package_or_stack_area",
    "total_dram_bandwidth": "GB/s aggregate IC-DRAM bandwidth",
}


def verify_technical_bounds(quoted_text, bounds):
    """Bind technical bounds to named source quantities and their native basis.

    Each parameter mention owns the following comparison phrases until the next
    named parameter. This handles a shared range (``2400 or more and less than
    4800``) and parenthesized definitional references without borrowing another
    quantity's nearby number. This deliberately narrow grammar covers the
    registered issued-rule extracts; it is not a general legal-text parser.
    """
    if not bounds:
        return True  # some quoted descriptive/definition claims have no coding
    text = quoted_text.replace(",", "")
    named = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _PARAMETER_NAMES.items()), re.I)
    mentions = list(named.finditer(text))
    parsed = []
    comparison = re.compile(r"(?P<relation>greater than|less than)\s+(?P<before>\d+(?:\.\d+)?)|"
                            r"(?P<after>\d+(?:\.\d+)?)\s+or\s+(?P<inclusive>more|less)", re.I)
    for i, mention in enumerate(mentions):
        variable = mention.lastgroup
        end = mentions[i + 1].start() if i + 1 < len(mentions) else len(text)
        segment = text[mention.end():end]
        for match in comparison.finditer(segment):
            if match["relation"]:
                sign = ">" if match["relation"].lower() == "greater than" else "<"
                value = Decimal(match["before"])
            else:
                sign = ">=" if match["inclusive"].lower() == "more" else "<="
                value = Decimal(match["after"])
            parsed.append((variable, sign, value))
    coded = []
    for bound in bounds:
        variable = bound["variable"]
        if variable not in _PARAMETER_NAMES or bound["native_unit"] != _PARAMETER_UNITS[variable]:
            raise ValueError("Technical bound variable/native-unit basis is not registered")
        if bound["operator"] not in {"<", "<=", ">", ">="}:
            raise ValueError("Technical bound operator is not registered")
        value = Decimal(str(bound["value"]))
        if not value.is_finite() or value < 0:
            raise ValueError("Technical bound value must be finite and nonnegative")
        coded.append((variable, bound["operator"], value))
    if Counter(coded) != Counter(parsed):
        raise ValueError("Technical bound variable/value/operator does not match its named source phrase")
    return True
