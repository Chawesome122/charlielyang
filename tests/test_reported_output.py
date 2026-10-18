import pytest
import pandas as pd
from weaponized.rare_earths.reported_output import hindcasts

from weaponized.rare_earths.reported_output import fiscal_quarter_end, parse_lynas_quarterly_front_page


def test_australian_fiscal_calendar_crosses_calendar_year():
    assert [fiscal_quarter_end(f"Q{i} FY24") for i in range(1, 5)] == [
        "2023-09-30", "2023-12-31", "2024-03-31", "2024-06-30"]


def test_comparative_quarters_and_units_are_preserved():
    page = """FOR THE PERIOD ENDED 30 JUNE 2025
    Q4 FY24    Q3 FY25    Q4 FY25
    Total REO production: 2,188t 1,911t 3,212t
    NdPr production: 1,504t 1,509t 2,080t
    CEO REVIEW"""
    rows = parse_lynas_quarterly_front_page(page)
    assert len(rows) == 6
    assert rows[0]["period_end"] == "2024-06-30"
    assert rows[-1]["value"] == 2080
    assert rows[-1]["comparative"] is False
    assert rows[0]["comparative"] is True
    with pytest.raises(ValueError, match="inconsistent"):
        parse_lynas_quarterly_front_page(page.replace("30 JUNE", "31 MARCH"))
    with pytest.raises(ValueError, match="three explicitly"):
        parse_lynas_quarterly_front_page(page.replace("1,911t", "unknown"))


def test_late_revised_quarter_cannot_enter_earlier_hindcast():
    versions = pd.DataFrame([
        dict(period_end="2023-12-31", info_public_date="2024-01-22", product_basis="total_REO", value=10, source_id="old"),
        dict(period_end="2024-06-30", info_public_date="2024-07-23", product_basis="total_REO", value=12, source_id="latest"),
        dict(period_end="2024-12-31", info_public_date="2025-01-17", product_basis="total_REO", value=15, source_id="outcome"),
        dict(period_end="2023-12-31", info_public_date="2025-02-01", product_basis="total_REO", value=999, source_id="late_revision"),
    ])
    rows = hindcasts(versions)
    row = rows[rows.origin.eq("2024-09-30") & rows.method.eq("seasonal_previous_year")].iloc[0]
    assert row.prediction == 10
    assert row.training_sources == "old"
