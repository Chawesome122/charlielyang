import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.rare_earths.producer_measurement import asof_native, parse_mp_tables, producer_hindcasts, production_sales_comparison, reconcile_quarters, volume_cell

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def source():
    s=json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())["RE-MP-10K2024"]
    payload=(ROOT/s["archive_path"]).read_bytes()
    return payload,s["sha256"],parse_mp_tables(payload,s["sha256"],2024)


def test_source_quarter_header_and_native_values(source):
    rows=source[2]
    q={r["period_end"]:r["value"] for r in rows if r["variable"]=="NdPr_production" and r["table_kind"]=="quarterly"}
    assert [q[f"2024-{m}"] for m in ["03-31","06-30","09-30","12-31"]]==[131,272,478,413]
    assert q["2023-06-30"] is None
    # Upstream REO content is neither bulk concentrate mass nor NdPr output.
    annual=[r for r in rows if r["variable"]=="REO_production" and r["table_kind"]=="annual" and r["period_end"]=="2024-12-31"][0]
    assert annual["value"]==45455 and annual["product_basis"]=="REO_content_in_concentrate"


def test_dash_and_not_applicable_are_distinct(source):
    r=[r for r in source[2] if r["table_kind"]=="quarterly" and r["variable"]=="NdPr_sales" and r["period_end"]=="2023-09-30"][0]
    assert r["source_cell_token"]=="—" and r["value"] is None and r["cell_status"]=="displayed_dash"
    assert volume_cell("N/A")["cell_status"]=="not_applicable"
    assert volume_cell("0")["value"]==0


@pytest.mark.parametrize("token",["N/M","1.2","-1","1,23","nan","", "$"])
def test_unregistered_volume_cells_rejected(token):
    with pytest.raises(ValueError):volume_cell(token)


def test_hash_snapshot_integrity(source):
    with pytest.raises(ValueError,match="checksum"):parse_mp_tables(source[0]+b" ",source[1],2024)


def test_original_header_must_match_report(source):
    with pytest.raises(ValueError,match="header"):parse_mp_tables(source[0],source[1],2023)


def test_na_and_dash_table_arithmetic(source):
    rows=source[2]
    a=[r for r in rows if r["table_kind"]=="annual" and r["variable"]=="NdPr_sales" and r["period_end"]=="2023-12-31"][0]
    q=[r for r in rows if r["table_kind"]=="quarterly" and r["variable"]=="NdPr_sales" and r["period_end"].startswith("2023")]
    # N/A in early quarters means no fully numerical four-quarter identity;
    # it is not silently converted to zero to make an annual sum succeed.
    result=reconcile_quarters(a,q)
    assert result["status"]=="incomplete_numeric_support" and result["passed"] is None
    with pytest.raises(ValueError):reconcile_quarters(a,q[:3])


def test_inventory_currency_is_not_a_mass(source):
    rows=[r for r in source[2] if r["table_kind"]=="inventory_currency" and r["period_end"]=="2024-12-31"]
    v={r["variable"]:r["value"] for r in rows}
    assert v["current_total"]+v["noncurrent_portion"]==v["all_inventory_total"]==126936
    assert all(r["native_unit"]=="USD_thousands" for r in rows)


def test_asof_masks_retrospective_quarters(source):
    df=pd.DataFrame(source[2]);df["info_public_date"]="2025-02-28";df["source_id"]="RE-MP-10K2024"
    assert asof_native(df,"2024-12-31","quarterly").empty
    assert not asof_native(df,"2025-03-31","quarterly").empty
    with pytest.raises(ValueError):asof_native(df,"2026-10-12")


def test_kpi_subtraction_is_not_inventory():
    a=dict(period_end="2025-12-31",source_id="test",variable="NdPr_production",value=2599,cell_status="reported_number")
    b=a|dict(variable="NdPr_sales",value=1994)
    result=production_sales_comparison(a,b)
    assert result["descriptive_KPI_difference"]==605
    assert result["physical_stock_change"] is None and result["chemical_recovery"] is None
    assert result["China_free_service"] is None
    with pytest.raises(ValueError):production_sales_comparison(a,b|dict(source_id="later"))
    with pytest.raises(ValueError):production_sales_comparison(a,b|dict(variable="REO_sales"))


def test_source_definitions_do_not_imply_achieved_yields():
    rows=json.loads((ROOT/"codebooks/mp_measurement.json").read_text())["definitions"]
    illustrative=[r for r in rows if r["variable"]=="illustrative_sales_conversion_ratio"]
    assumed=[r for r in rows if r["variable"]=="assumed_sales_conversion_ratio"]
    assert illustrative[0]["value"]==1.25 and all(r["value"]==1.2 for r in assumed)
    assert any(r["variable"]=="internal_sales_included" for r in rows)
    assert not any("recovery" in r["variable"] for r in rows)


def test_common_support_and_release_masks():
    data=pd.read_csv(ROOT/"data/processed/mp_measurement/native_cell_versions.csv")
    book=json.loads((ROOT/"codebooks/mp_measurement.json").read_text())
    p,a=producer_hindcasts(data,book["backtest_origins"])
    assert a.status.eq("eligible_common_support").sum()==9 and len(p)==27
    assert p.groupby("variable").origin.nunique().to_dict()==dict(NdPr_production=2,NdPr_sales=1,REO_production=3,REO_sales=3)
    assert (p.max_training_public_date<=p.origin).all()
    assert (p.max_training_period_end<=p.origin).all()
    assert (p.target>p.origin).all()
    assert not a[a.origin<"2024-02-28"].status.eq("eligible_common_support").any()


def test_later_comparatives_cannot_change_earlier_predictions():
    data=pd.read_csv(ROOT/"data/processed/mp_measurement/native_cell_versions.csv")
    origins=["2024-03-31","2024-06-30","2024-09-30"]
    before,_=producer_hindcasts(data,origins)
    data.loc[data.info_public_date.gt("2024-09-30") & data.value.notna(),"value"]*=1000
    after,_=producer_hindcasts(data,origins)
    # Later reports alter evaluation actuals, never origin-time forecasts.
    assert before.prediction.tolist()==after.prediction.tolist()
    assert before.actual.tolist()!=after.actual.tolist()


def test_numeric_identity_rejects_actual_discrepancy(source):
    rows=source[2]
    a=[r for r in rows if r["table_kind"]=="annual" and r["variable"]=="REO_production" and r["period_end"]=="2024-12-31"][0]
    q=[r for r in rows if r["table_kind"]=="quarterly" and r["variable"]=="REO_production" and r["period_end"].startswith("2024")]
    assert reconcile_quarters(a,q)["passed"]
    assert not reconcile_quarters(a|dict(value=a["value"]+1),q)["passed"]
    with pytest.raises(ValueError):reconcile_quarters(a,q[:3]+[q[3]|dict(period_end="2025-12-31")])
    with pytest.raises(ValueError):reconcile_quarters(a,q[:3]+[q[3]|dict(variable="REO_sales")])
    with pytest.raises(ValueError):reconcile_quarters(a|dict(source_id="old"),q)
