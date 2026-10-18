"""Minimal scientific schemas: unknown quantities remain nullable, never zero."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_id: str
    record_version_id: str
    entity_id: str
    variable: str
    value: float | str | None
    native_unit: str | None
    product_basis: str | None
    valid_date: date
    info_public_date: date
    source_id: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    locator: str
    evidence_class: Literal["empirical", "calibrated", "partial_identification", "scenario", "synthetic"]
    missing_reason: str | None = None
    event_kind: Literal["observed", "announcement", "target", "revision"] = "observed"

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.value is None and not self.missing_reason:
            raise ValueError("A missing observation needs a reason")
        if not self.locator.strip():
            raise ValueError("A source extraction locator is required")
        if self.evidence_class == "empirical" and self.info_public_date > date(2026, 10, 11):
            raise ValueError("Post-freeze empirical observation")
        return self


class ProjectEvent(BaseModel):
    project_id: str
    facility_id: str
    stage: Literal["mine", "separation", "metal_alloy", "magnet"]
    from_state: Literal["A", "F", "I", "C", "Q", "O", "S", "X"] | None
    to_state: Literal["A", "F", "I", "C", "Q", "O", "S", "X"]
    valid_date: date
    info_public_date: date
    source_id: str
    lower_date: date | None = None
    upper_date: date | None = None
    independently_verified: bool = False

    @model_validator(mode="after")
    def interval_order(self):
        if self.lower_date and self.upper_date and self.lower_date > self.upper_date:
            raise ValueError("Reversed censoring interval")
        return self
