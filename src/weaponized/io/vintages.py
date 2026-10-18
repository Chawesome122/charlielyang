"""Two-clock selection without retroactive visibility of revisions."""
from datetime import date
from pathlib import Path
import pandas as pd

FREEZE = date(2026, 10, 11)


def select_asof(table: pd.DataFrame, as_of: str | date,
                keys: tuple[str, ...] = ("observation_id",)) -> pd.DataFrame:
    """Latest *publicly available* version, including tombstones before filtering.

    `valid_date` is event time. Announcements about future events are admissible
    information, but are not observations of completed events.
    """
    cutoff = pd.Timestamp(as_of)
    if cutoff > pd.Timestamp(FREEZE):
        raise ValueError("Research information freeze exceeded")
    required = {*keys, "info_public_date", "record_version_id"}
    if missing := required - set(table.columns):
        raise ValueError(f"Missing vintage columns: {sorted(missing)}")
    data = table.copy()
    data["info_public_date"] = pd.to_datetime(data.info_public_date, errors="raise")
    data = data[data.info_public_date.notna() & (data.info_public_date <= cutoff)]
    # Ambiguous equally dated revisions require adjudication, never arbitrary order.
    if data.duplicated([*keys, "info_public_date"]).any():
        raise ValueError("Ambiguous same-publication-date revisions")
    data = data.sort_values("info_public_date").drop_duplicates(list(keys), keep="last")
    if "withdrawn" in data:
        data = data[~data.withdrawn.fillna(False).astype(bool)]
    return data.reset_index(drop=True)


def load_asof(table_name: str, as_of: str | date,
               data_root: str | Path = "data/processed") -> pd.DataFrame:
    root = Path(data_root).resolve()
    path = (root / f"{table_name}.csv").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Table must remain within data root")
    return select_asof(pd.read_csv(path), as_of)


def event_observed(table: pd.DataFrame, as_of: str | date) -> pd.DataFrame:
    """Completed-event panel excludes future announced targets separately."""
    selected = select_asof(table, as_of)
    return selected[pd.to_datetime(selected.valid_date) <= pd.Timestamp(as_of)].copy()
