"""Versioned legal records without equating authorization and prohibition."""

from __future__ import annotations

import pandas as pd
import xml.etree.ElementTree as ET

LEGAL_COLUMNS = [
    "policy_id", "instrument_id", "version_id", "jurisdiction", "issuer",
    "official_language", "publication_date", "effective_date", "end_date",
    "info_public_date", "retrieval_timestamp", "sha256", "technology_layer",
    "product_code", "legal_citation", "destination", "end_user", "end_use",
    "person_scope", "license_requirement", "review_presumption", "exemption",
    "status", "severity_ordinal", "scope_coverage", "confidence", "source_id",
    "adjudication_id", "supersedes_version", "evidence_verified",
]


def issued_xml_text(payload: bytes, document_number: str) -> str:
    """Read original issued XML, rejecting a mismatched document or HTML page."""
    root = ET.fromstring(payload)
    if root.tag not in {"RULE", "NOTICE", "PRORULE"}:
        raise ValueError("Expected original Federal Register issued-document XML")
    text = " ".join(" ".join(root.itertext()).split())
    if f"[FR Doc. {document_number} Filed " not in text:
        raise ValueError("Federal Register document identity mismatch")
    return text


def validate_legal_events(frame):
    missing = set(LEGAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing legal schema fields: {sorted(missing)}")
    if frame.version_id.duplicated().any():
        raise ValueError("Legal version identifiers must be immutable and unique")
    if frame.empty:
        return True
    for column in ["policy_id", "instrument_id", "version_id", "info_public_date", "source_id", "sha256"]:
        if frame[column].isna().any():
            raise ValueError(f"Required provenance missing: {column}")
    if not frame.sha256.str.fullmatch(r"[0-9a-f]{64}").all():
        raise ValueError("Source artifact requires SHA256")
    valid_severity = frame.severity_ordinal.dropna().isin([0, .25, .5, .75, 1]).all()
    if not valid_severity:
        raise ValueError("Legal severity must follow the registered ordinal anchors")
    if not frame.status.isin(["proposed", "in_force", "stayed", "repealed", "superseded"]).all():
        raise ValueError("Unknown legal status")
    if not frame.license_requirement.isin(["none", "required", "prohibited", "general_authorization", "unknown"]).all():
        raise ValueError("Use explicit license requirement, not a generic ban flag")
    # A source supporting only 'required' cannot justify a complete-access loss.
    for column in ["publication_date", "effective_date", "end_date", "info_public_date"]:
        pd.to_datetime(frame[column].dropna(), errors="raise")
    # Public inspection and advance official notices can precede the Federal
    # Register publication. The earlier public clock needs its own locator.
    return True


def legal_asof(frame, as_of):
    """Retain observed instrument versions, then evaluate their legal clock.

    Amendments with separate scope must have separate instrument IDs. A
    genuinely replacing amendment may share an instrument ID and must set
    supersedes_version. An explicit suspension/repeal needs its own public
    version. Old rows are never overwritten to backdate later knowledge.
    """
    validate_legal_events(frame)
    if frame.empty:
        return frame.assign(status_asof=pd.Series(dtype=str))
    as_of = pd.Timestamp(as_of)
    observed = frame.loc[(pd.to_datetime(frame.info_public_date) <= as_of) & frame.evidence_verified.eq(True)].copy()
    observed = observed.sort_values(["info_public_date", "publication_date", "version_id"])
    # A replacement changes the full scope of the same instrument only.
    effective_replacing = set(
        observed.loc[pd.to_datetime(observed.effective_date) <= as_of, "supersedes_version"].dropna()
    )
    observed = observed.loc[~observed.version_id.isin(effective_replacing)].copy()
    def status(row):
        if pd.isna(row.effective_date) or pd.Timestamp(row.effective_date) > as_of:
            return "announced_not_effective"
        if pd.notna(row.end_date) and pd.Timestamp(row.end_date) < as_of:
            return "ended"
        return row.status
    observed["status_asof"] = observed.apply(status, axis=1)
    return observed
