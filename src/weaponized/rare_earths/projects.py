"""Project risk-set definitions; dates of events and disclosure remain separate."""
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Mapping

STATES = ("A", "F", "I", "C", "Q", "O", "S", "X")
STATE_LABELS = dict(zip(STATES, ("announced", "feasibility/permitting", "financing/FID",
    "construction", "testing/commissioning", "operating", "suspended", "cancelled")))
# Suspension relaunch is restricted further to its recorded resume state in simulation.
ALLOWED = {"A": ("F", "S", "X"), "F": ("I", "S", "X"), "I": ("C", "S", "X"),
    "C": ("Q", "S", "X"), "Q": ("O", "S", "X"), "O": ("S", "X"),
    "S": ("F", "I", "C", "Q", "O", "X"), "X": ()}


def quarter_index(value: str) -> int:
    """2028Q4 -> integer clock; each tick is exactly one quarter."""
    if len(value) != 6 or value[4] != "Q" or value[-1] not in "1234":
        raise ValueError(f"Invalid quarter {value!r}")
    return int(value[:4]) * 4 + int(value[-1]) - 1


def quarter_label(value: int) -> str:
    return f"{value // 4:04d}Q{value % 4 + 1}"


@dataclass(frozen=True)
class ProjectSnapshot:
    activity_id: str
    project_id: str
    group_id: str
    stage: str
    state: str
    state_age_quarters: int
    info_public_date: date
    # O-state commissioning may precede observation (left truncation).
    commissioning_quarter: int | None = None
    resume_state: str | None = None
    target_commission_quarter: int | None = None
    country: str | None = None
    lagged_covariates: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.state not in STATES or self.state_age_quarters < 0:
            raise ValueError("Invalid state or age")
        if self.state == "S" and self.resume_state not in STATES[:6]:
            raise ValueError("Suspended activity requires an independently recorded resume state")


@dataclass(frozen=True)
class ProjectEvent:
    activity_id: str
    from_state: str
    to_state: str
    event_date_lower: date
    event_date_upper: date
    info_public_date: date
    source_id: str

    def __post_init__(self):
        if self.to_state not in ALLOWED.get(self.from_state, ()):
            raise ValueError("Impossible transition; retrospective missing stages need an observation model")
        if self.event_date_lower > self.event_date_upper:
            raise ValueError("Reversed event interval")
        if self.info_public_date < self.event_date_upper:
            raise ValueError("Announcements of future targets are not realized events")


def asof_events(events: Iterable[ProjectEvent], origin: date) -> list[ProjectEvent]:
    """Never backfill a later public confirmation into an earlier forecast."""
    return [event for event in events if event.info_public_date <= origin]


def validate_snapshot(snapshot: Iterable[ProjectSnapshot], origin: date) -> list[ProjectSnapshot]:
    rows = list(snapshot)
    if len({p.activity_id for p in rows}) != len(rows):
        raise ValueError("Duplicate activity capacity; expansion phases require distinct activity IDs")
    if any(p.info_public_date > origin for p in rows):
        raise ValueError("Snapshot contains information released after its origin")
    return rows
