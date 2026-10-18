from datetime import date
import pandas as pd
import pytest
from weaponized.io.archive import archive_bytes, sha256_file
from weaponized.io.vintages import select_asof, event_observed
from weaponized.io.schemas import Claim


def fixture():
    return pd.DataFrame([
        dict(observation_id="p", record_version_id="v1", value=10, valid_date="2023-01-01", info_public_date="2024-02-10"),
        dict(observation_id="p", record_version_id="v2", value=8, valid_date="2023-01-01", info_public_date="2025-01-01"),
        dict(observation_id="future", record_version_id="v1", value=99, valid_date="2028-01-01", info_public_date="2024-01-01"),
        dict(observation_id="unknown", record_version_id="v1", value=5, valid_date="2020-01-01", info_public_date=None)])


def test_revisions_are_not_backdated():
    df = fixture()
    assert select_asof(df, "2023-12-31").empty
    assert select_asof(df, "2024-12-31").set_index("observation_id").loc["p", "value"] == 10
    assert select_asof(df, "2025-12-31").set_index("observation_id").loc["p", "value"] == 8
    assert set(event_observed(df, "2024-12-31").observation_id) == {"p"}


def test_freeze_and_ambiguous_revisions():
    with pytest.raises(ValueError): select_asof(fixture(), "2027-01-01")
    data = fixture()
    with pytest.raises(ValueError): select_asof(pd.concat([data, data.iloc[[0]]]), "2025-01-01")


def test_content_addressed_archive(tmp_path):
    one = archive_bytes(b"old source", tmp_path)
    two = archive_bytes(b"new source", tmp_path)
    assert one != two and one.read_bytes() == b"old source"
    assert archive_bytes(b"old source", tmp_path) == one
    one.write_bytes(b"corrupt")
    with pytest.raises(ValueError): archive_bytes(b"old source", tmp_path)


def test_claim_rejects_undocumented_missing_and_future_information():
    base = dict(observation_id="a", record_version_id="1", entity_id="p", variable="capacity", value=None,
                native_unit="t/y", product_basis="oxide", valid_date="2023-01-01", info_public_date="2024-02-10",
                source_id="s", source_sha256="0"*64, locator="Table 1", evidence_class="empirical")
    with pytest.raises(ValueError): Claim(**base)
    assert Claim(**base, missing_reason="not disclosed").value is None
    with pytest.raises(ValueError): Claim(**(base | dict(info_public_date="2026-10-12")), missing_reason="not disclosed")
