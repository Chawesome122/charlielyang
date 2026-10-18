import math

import pytest

from weaponized.rare_earths.materials import reported_batch_summary
from weaponized.rare_earths.evidence import capacity_time_basis, documented_activity_snapshot
import pandas as pd


def test_reported_product_ratio_is_neither_recovery_nor_annual_capacity():
    batch = reported_batch_summary(1.2, 3.0)
    assert batch["magnet_to_oxide_product_mass_ratio"] == pytest.approx(2.5)
    assert batch["minimum_additional_input_mass_tonnes"] == pytest.approx(1.8)
    assert reported_batch_summary(3.0, 1.2)["minimum_additional_input_mass_tonnes"] == 0
    assert batch["elemental_recovery_estimate"] is None
    assert batch["annual_capacity_estimate"] is None
    assert batch["china_free_service_estimate"] is None


@pytest.mark.parametrize("bad", [0, -1, math.inf, math.nan])
def test_batch_mass_must_be_finite_positive(bad):
    with pytest.raises(ValueError):
        reported_batch_summary(bad, 3.0)


def test_campaign_total_is_not_annual_even_when_unit_contains_per_year():
    assert capacity_time_basis(10, "native tons TOTAL demonstration campaign, not per year") == "finite_batch_or_campaign_total"
    assert capacity_time_basis(3000, "tonnes/year planned nameplate") == "annual_native_capacity"
    assert capacity_time_basis(3000, "total REO tonnes/year") == "annual_native_capacity"
    assert capacity_time_basis(None, "tonnes/year") == "missing"


def test_documentary_snapshot_excludes_future_versions_and_retains_undated_gap():
    frame = pd.DataFrame([
        dict(record_id="a", activity_id="plant", info_public_date="2025-01-01", valid_date="2024-12-31", capacity_native=100, native_unit="tonnes/year"),
        dict(record_id="b", activity_id="plant", info_public_date="2026-10-12", valid_date="2024-12-31", capacity_native=9999, native_unit="tonnes/year"),
        dict(record_id="c", activity_id="unknown", info_public_date=None, valid_date=None, capacity_native=None, native_unit=None),
    ])
    result = documented_activity_snapshot(frame).set_index("activity_id")
    assert result.loc["plant", "capacity_native"] == 100
    assert not result.loc["unknown", "public_clock_eligible"]
    assert not result.independent_stable_qualified_rate_verified.any()
