"""Issuer-native MP volume tables; these are not a material-flow ledger.

An oxide-equivalent sales KPI can include internal transfers and assumed metal
conversions. Currency inventories and production-minus-sales do not identify
physical opening stocks, recovery yields or final magnet service.
"""
import hashlib
import math
import re

from bs4 import BeautifulSoup
import pandas as pd

from weaponized.io.original_text import normalize_evidence

KPI_ROWS = {
    "REO Production Volume (MTs)": ("REO_production", "REO_content_in_concentrate"),
    "REO Sales Volume (MTs)": ("REO_sales", "REO_content_in_concentrate"),
    "NdPr Production Volume (MTs)": ("NdPr_production", "NdPr_oxide_production_KPI"),
    "NdPr Sales Volume (MTs)": ("NdPr_sales", "NdPr_oxide_equivalent_sales_KPI"),
}
INVENTORY_ROWS = {
    "Raw materials and supplies, including spare parts": "raw_materials_supplies",
    "Raw materials and supplies, including spare parts (1)": "raw_materials_supplies",
    "Mined ore stockpiles": "mined_ore_stockpiles",
    "Work in process": "work_in_process",
    "Finished goods": "finished_goods",
    "Total current inventories": "current_total",
    "Add: Non-current portion (1)": "noncurrent_portion",
    "Add: Non-current portion (2)": "noncurrent_portion",
    "Total inventories": "all_inventory_total",
}


def volume_cell(token):
    if token == "N/A":
        return dict(value=None, cell_status="not_applicable", missing_reason="issuer N/A; not recoded as measured zero")
    if token == "—":
        return dict(value=None, cell_status="displayed_dash", missing_reason="issuer dash; zero used only in displayed-table arithmetic")
    if not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)", token):
        raise ValueError(f"Invalid native volume cell: {token}")
    return dict(value=int(token.replace(",", "")), cell_status="reported_number", missing_reason=None)


def parse_mp_tables(payload: bytes, digest: str, report_year: int):
    """Hash and parse the same immutable snapshot; bind cells to their headers.

    Annual change/percent columns are explicitly excluded. Empty HTML padding
    cells and currency symbols are excluded only after preserving row labels.
    """
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Original MP source checksum mismatch")
    soup = BeautifulSoup(payload.decode("utf-8"), "html.parser")
    records, table_counts = [], {"annual": 0, "quarterly": 0, "inventory_currency": 0}
    for ordinal, table in enumerate(soup.find_all("table")):
        text = normalize_evidence(table.get_text(" ", strip=True))
        if "REO Production Volume (MTs)" in text and "REO Sales Volume (MTs)" in text:
            if "Year ended December 31," in text and "Amount Change" in text:
                kind = "annual"
                header = re.search(r"except percentages\) (\d{4}) (\d{4}) (\d{4})", text)
                if not header or [int(x) for x in header.groups()] != [report_year, report_year-1, report_year-2]:
                    raise ValueError("Ambiguous annual KPI year header")
                periods = [f"{int(y)}-12-31" for y in header.groups()]
            elif "FY" in text and "Q4" in text:
                kind = "quarterly"
                header = re.findall(r"FY(\d{4})", text.split("Rare earth concentrate")[0])
                quarters = re.findall(r"\bQ[1-4]\b", text.split("Rare earth concentrate")[0])
                if [int(y) for y in header] != [report_year, report_year-1, report_year-2] or quarters != ["Q4","Q3","Q2","Q1"]*3:
                    raise ValueError("Ambiguous quarterly KPI year/quarter header")
                periods = [str(pd.Period(f"{y}Q{q}").end_time.date()) for y in header for q in [4,3,2,1]]
            else:
                raise ValueError("Unrecognized MP KPI table")
            mapping = KPI_ROWS
        elif "Total inventories" in text and "Mined ore stockpiles" in text:
            kind, mapping = "inventory_currency", INVENTORY_ROWS
            header = re.search(r"\(in thousands\) (\d{4}) (\d{4})", text)
            if not header or [int(x) for x in header.groups()] != [report_year, report_year-1]:
                raise ValueError("Ambiguous inventory year/currency header")
            periods = [f"{y}-12-31" for y in header.groups()]
        else:
            continue
        table_counts[kind] += 1
        seen = set()
        for row_ordinal, tr in enumerate(table.find_all("tr")):
            cells = [normalize_evidence(c.get_text(" ",strip=True)) for c in tr.find_all(["td","th"], recursive=False)]
            cells = [c for c in cells if c and c != "$"]
            if not cells or cells[0] not in mapping:
                continue
            label = cells[0]
            variable, product = mapping[label] if kind != "inventory_currency" else (mapping[label], "mixed_inventory_book_value")
            if variable in seen:
                raise ValueError("Duplicate named KPI/inventory row")
            seen.add(variable)
            tokens = cells[1:]
            if kind != "annual" and len(tokens) != len(periods):
                raise ValueError("Native table cell count does not match header")
            if len(tokens) < len(periods):
                raise ValueError("Missing annual KPI cells")
            for period, token in zip(periods, tokens):
                parsed = volume_cell(token)
                if kind == "inventory_currency" and parsed["value"] is None:
                    raise ValueError("Unregistered nullable monetary inventory")
                records.append(dict(period_end=period, variable=variable, product_basis=product,
                                    native_unit="USD_thousands" if kind == "inventory_currency" else "issuer_KPI_metric_tonnes",
                                    table_kind=kind, source_cell_token=token, **parsed,
                                    comparative=int(period[:4]) != report_year,
                                    locator=f"10-K original HTML table {ordinal}; row {row_ordinal}; period {period}; {label}",
                                    quote=text, table_ordinal=ordinal, row_ordinal=row_ordinal))
        expected = len(KPI_ROWS) if kind != "inventory_currency" else 7
        if len(seen) != expected:
            raise ValueError("Required named KPI/inventory rows absent")
    if table_counts["annual"] != 1 or table_counts["inventory_currency"] != 1 or table_counts["quarterly"] != (report_year != 2025):
        raise ValueError("Unexpected MP native table coverage")
    return records


def reconcile_quarters(annual_row, quarters):
    """N/A stays N/A; displayed dashes contribute zero only to this identity."""
    if len(quarters) != 4 or len({r["period_end"] for r in quarters}) != 4:
        raise ValueError("Four distinct quarterly cells required")
    expected={str(pd.Period(f"{annual_row['period_end'][:4]}Q{q}").end_time.date()) for q in range(1,5)}
    if {r["period_end"] for r in quarters} != expected or any(r["variable"]!=annual_row["variable"] for r in quarters):
        raise ValueError("Quarterly period/metric must match the annual cell")
    if any(r.get("source_id")!=annual_row.get("source_id") for r in quarters):
        raise ValueError("Quarter/annual source vintages differ")
    if annual_row["cell_status"] == "not_applicable":
        return dict(passed=all(r["cell_status"] == "not_applicable" for r in quarters),
                    status="all_not_applicable", quarter_sum=None, annual_value=None)
    if annual_row["cell_status"] != "reported_number" or any(r["cell_status"] == "not_applicable" for r in quarters):
        return dict(passed=None, status="incomplete_numeric_support", quarter_sum=None, annual_value=annual_row["value"])
    total = sum(0 if r["cell_status"] == "displayed_dash" else r["value"] for r in quarters)
    return dict(passed=total == annual_row["value"], status="numeric_identity", quarter_sum=total, annual_value=annual_row["value"])


def asof_native(versions, origin, kind="annual", freeze="2026-10-11"):
    if origin > freeze:
        raise ValueError("Origin exceeds research information freeze")
    known = versions[versions.info_public_date.le(origin) & versions.period_end.le(origin) & versions.table_kind.eq(kind)]
    return known.sort_values(["info_public_date","source_id"]).drop_duplicates(["period_end","variable"],keep="last")


def production_sales_comparison(production, sales):
    if production["period_end"] != sales["period_end"] or production["source_id"] != sales["source_id"]:
        raise ValueError("Comparison needs matched period/source vintage")
    pair = (production["variable"],sales["variable"])
    if pair not in {("REO_production","REO_sales"),("NdPr_production","NdPr_sales")}:
        raise ValueError("Unmatched stages/metrics cannot be subtracted")
    if production["cell_status"] != "reported_number" or sales["cell_status"] != "reported_number":
        raise ValueError("Comparison requires reported numerical cells")
    if any(not math.isfinite(r["value"]) or r["value"]<0 for r in [production,sales]):
        raise ValueError("KPI values must be finite and nonnegative")
    return dict(descriptive_KPI_difference=production["value"]-sales["value"],
                physical_stock_change=None, chemical_recovery=None, China_free_service=None,
                interpretation="Reported KPI subtraction only; internal use, losses, timing, measurement conventions and stocks are not reconciled")


def producer_hindcasts(versions, origins, freeze="2026-10-11"):
    """Common-support naive comparisons, never filling N/A or missing reports.

    Actuals are latest source-visible cells by the freeze. Inputs are separately
    selected at each origin. The actual-vintage convention is not real-time
    first-release evaluation, and the small archive subset is not all public data.
    """
    actual = asof_native(versions,freeze,"quarterly",freeze)
    forecasts, audit = [], []
    for origin in origins:
        period=pd.Period(origin,freq="Q")
        origin_date=str(period.end_time.date())
        target=str((period+1).end_time.date())
        seasonal=str((period-3).end_time.date())
        known=asof_native(versions,origin_date,"quarterly",freeze)
        for variable,_ in KPI_ROWS.values():
            train=known[known.variable.eq(variable) & known.cell_status.eq("reported_number")]
            outcome=actual[actual.variable.eq(variable) & actual.period_end.eq(target) & actual.cell_status.eq("reported_number")]
            prior=train[train.period_end.eq(seasonal)]
            status=("target_not_observed_numeric" if outcome.empty else "no_released_numeric_history" if train.empty
                    else "seasonal_comparator_not_reported_numeric" if prior.empty else "eligible_common_support")
            audit.append(dict(origin=origin_date,target=target,variable=variable,status=status,
                              available_numeric_quarters=len(train),actual_vintage="latest source-visible by research freeze"))
            if status != "eligible_common_support":
                continue
            last=train.sort_values("period_end").iloc[-1]
            for method, selected in [("latest_available_persistence",train[train.period_end.eq(last.period_end)]),
                                     ("seasonal_previous_year",prior),("available_history_mean",train)]:
                prediction=float(selected.value.mean())
                value=float(outcome.iloc[0].value)
                forecasts.append(dict(origin=origin_date,target=target,variable=variable,method=method,
                                      prediction=prediction,actual=value,error=prediction-value,
                                      max_training_public_date=selected.info_public_date.max(),
                                      max_training_period_end=selected.period_end.max(),
                                      training_sources="|".join(sorted(selected.source_id.unique())),
                                      outcome_source=outcome.iloc[0].source_id,outcome_public_date=outcome.iloc[0].info_public_date,
                                      native_unit="issuer_KPI_metric_tonnes",system_service_forecast=False))
    return pd.DataFrame(forecasts),pd.DataFrame(audit)
