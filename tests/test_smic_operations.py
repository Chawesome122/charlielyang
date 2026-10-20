import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from weaponized.io.original_text import verified_original_text
from weaponized.semiconductors.operations import asof_operations, parse_smic_operations, revenue_decomposition, smic_definition_quotes, wafer_revenue_bridge

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def original():
    book=json.loads((ROOT/"codebooks/smic_operations.json").read_text())
    spec=book["sources"][-1]
    source=pd.read_csv(ROOT/"metadata/semiconductor_sources.csv").set_index("source_id").loc[spec["source_id"]]
    text=verified_original_text(ROOT/source.path,source.sha256)
    return spec,text


def test_named_cells_and_reporting_windows(original):
    rows=parse_smic_operations(original[1],original[0])
    values={r["variable"]:r for r in rows if r["period_end"]=="2025-12-31"}
    assert len(rows)==30
    assert values["wafer_shipments"]["value"]==2514970
    assert values["monthly_capacity"]["value"]==1058750
    assert values["monthly_capacity"]["measurement_timing"]=="monthly_rate_reported_for_quarter"
    assert values["capacity_utilization"]["value"]==95.7
    assert values["annual_utilization_summary"]["value"]==93.5
    assert values["rounded_yearend_monthly_capacity"]["value"]==1059
    assert values["rounded_yearend_monthly_capacity"]["native_unit"].startswith("thousand_")
    assert values["rd_expense"]["value"]==239676
    assert values["capital_expenditure"]["value"]==2407.5
    assert max(r["period_end"] for r in rows)=="2025-12-31"  # 2026 guidance is not an observation.


def test_later_page_date_cannot_supply_first_page_clock(original):
    pages=original[1].split("\f")
    pages[0]=pages[0].replace("February 10, 2026","DATE REMOVED")
    pages[-1]+=" February 10, 2026"
    with pytest.raises(ValueError,match="page 1"):parse_smic_operations("\f".join(pages),original[0])


def test_future_source_or_wrong_quarter_header_rejected(original):
    with pytest.raises(ValueError,match="Post-freeze"):parse_smic_operations(original[1],original[0]|dict(info_public_date="2026-10-12"))
    wrong=original[1].replace("4Q25","TEMP").replace("3Q25","4Q25").replace("TEMP","3Q25")
    with pytest.raises(ValueError,match="header"):parse_smic_operations(wrong,original[0])


def test_missing_named_source_row_is_not_zero(original):
    text=original[1].replace("Wafer shipments(1)","Unregistered output(1)")
    with pytest.raises(ValueError):parse_smic_operations(text,original[0])


def test_wafer_size_percentages_are_revenue_shares(original):
    rows=parse_smic_operations(original[1],original[0])
    r=next(r for r in rows if r["variable"]=="wafer_12inch_revenue_share" and r["period_end"]=="2025-12-31")
    assert r["value"]==77.2 and r["product_basis"]=="share_of_wafer_revenue_not_physical_output"


def test_exact_source_denominator_definitions_are_retained(original):
    definitions={r["definition"]:r for r in smic_definition_quotes(original[1],original[0])}
    assert "Based on standard logic 8-inch equivalent wafers" in definitions["shipment_equivalent_basis"]["quote"]
    assert "total wafers out divided by estimated total quarterly capacity" in definitions["utilization_denominator"]["quote"]
    assert definitions["utilization_denominator"]["pdf_page"]==5
    vintages=pd.read_csv(ROOT/"data/processed/smic_operations/comparative_vintages.csv")
    assert (~vintages.definition_wording_agrees).sum()==2


def test_retrospective_comparative_wording_is_vintaged():
    data=pd.read_csv(ROOT/"data/processed/smic_operations/observations.csv")
    early=asof_operations(data,"2024-12-31")
    late=asof_operations(data,"2026-10-11")
    a=early[early.variable.eq("wafer_shipments") & early.period_end.eq("2023-12-31")].iloc[0]
    b=late[late.variable.eq("wafer_shipments") & late.period_end.eq("2023-12-31")].iloc[0]
    assert a.value==b.value==1675002
    assert a.product_basis=="generic_8inch_equivalent"
    assert b.product_basis=="standard_logic_8inch_equivalent"
    assert not early.period_end.eq("2024-12-31").any()
    with pytest.raises(ValueError):asof_operations(data,"2026-10-12")


def test_current_and_comparative_financial_periods_are_separate():
    data=pd.read_csv(ROOT/"data/processed/smic_operations/observations.csv")
    part=data[data.source_id.eq("SC-SMIC-FY2023-EARNINGS") & data.variable.eq("rd_expense")].set_index("period_end")
    assert part.loc["2023-12-31","value"]==189138
    assert part.loc["2022-12-31","value"]==197455


def test_revenue_bridge_does_not_identify_price_yield_or_target_states():
    r=wafer_revenue_bridge(1000,80,200)
    assert r["wafer_attributed_revenue_usd"]==800
    assert r["nominal_wafer_revenue_per_reported_equivalent_shipment"]==4
    assert all(r[k] is None for k in ["quality_adjusted_price","advanced_node_yield","domestic_capability_z","foreign_access_f","combined_availability_a"])


@pytest.mark.parametrize("values",[(0,80,200),(-1,80,200),(1000,0,200),(1000,101,200),(1000,80,0),(np.nan,80,200),(1000,np.inf,200)])
def test_invalid_bridge_inputs_rejected(values):
    with pytest.raises(ValueError):wafer_revenue_bridge(*values)


def test_log_accounting_identity_and_inconsistent_ratio():
    a=dict(shipments=200,**wafer_revenue_bridge(1000,80,200))
    b=dict(shipments=100,**wafer_revenue_bridge(900,80,100))
    result=revenue_decomposition(a,b)
    assert result["passed"] and abs(result["identity_residual"])<1e-12
    assert result["causal_effect"] is None and result["technological_substitution"] is None
    assert not revenue_decomposition(a|dict(nominal_wafer_revenue_per_reported_equivalent_shipment=99),b)["passed"]


def test_all_actual_cells_have_primary_page_locators_and_no_target_scores():
    data=pd.read_csv(ROOT/"data/processed/smic_operations/observations.csv")
    assert len(data)==120 and data.pdf_page.ge(1).all()
    assert not data.target_specific_capability_identified.any()
    assert not data.foreign_access_identified.any()
    assert not data.combined_availability_identified.any()
    assert data.info_public_date.le("2026-10-11").all()
