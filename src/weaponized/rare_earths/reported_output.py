"""Extract issuer-native quarterly KPIs without converting them into service.

The three columns on a Lynas quarterly report's first page are explicitly
labelled fiscal quarters. Comparative values remain separate source vintages.
"""
from datetime import date
import re

import pandas as pd


def fiscal_quarter_end(label: str) -> str:
    match = re.fullmatch(r"Q([1-4]) FY(\d{2})", label)
    if not match:
        raise ValueError(f"Invalid Australian fiscal quarter: {label}")
    quarter, fiscal_year = int(match[1]), 2000 + int(match[2])
    year, month, day = {
        1: (fiscal_year - 1, 9, 30), 2: (fiscal_year - 1, 12, 31),
        3: (fiscal_year, 3, 31), 4: (fiscal_year, 6, 30),
    }[quarter]
    return date(year, month, day).isoformat()


def parse_lynas_quarterly_front_page(page: str) -> list[dict]:
    period = re.search(r"FOR THE PERIOD ENDED\s+(\d{1,2} [A-Z]+ \d{4})", page)
    if not period:
        raise ValueError("Quarterly reporting-period header missing")
    from datetime import datetime
    current = datetime.strptime(period[1], "%d %B %Y").date().isoformat()
    labels = re.findall(r"Q[1-4]\s+FY\d{2}", page.split("CEO REVIEW")[0])
    labels = [" ".join(label.split()) for label in labels]
    if len(labels) != 3 or fiscal_quarter_end(labels[-1]) != current:
        raise ValueError("Ambiguous or inconsistent three-column quarter header")
    rows = []
    for product, pattern in [
        ("total_REO", r"Total REO production:\s*(.*)"),
        ("NdPr_oxide_product_family", r"NdPr production:\s*(.*)"),
    ]:
        line = re.search(pattern, page)
        if not line:
            raise ValueError(f"Missing KPI: {product}")
        cells = re.findall(r"([\d,]+)\s*(REOt|t)\b", line[1])
        if len(cells) != 3:
            raise ValueError(f"Expected three explicitly unit-labelled cells: {line[0]}")
        for i, (label, (amount, token)) in enumerate(zip(labels, cells)):
            rows.append(dict(period_end=fiscal_quarter_end(label), fiscal_quarter=label,
                             product_basis=product, value=int(amount.replace(",", "")),
                             native_unit="reported oxide/product-family tonnes",
                             source_unit_token=token, comparative=(i != 2),
                             report_period_end=current, locator="PDF page 1; highlights: " + line[0]))
    return rows


def hindcasts(versions, freeze="2026-10-11"):
    versions = versions[versions.info_public_date.le(freeze)].copy()
    actual = versions.sort_values("info_public_date").drop_duplicates(["period_end", "product_basis"], keep="last")
    predictions = []
    for origin in pd.period_range("2023Q4", "2026Q1", freq="Q"):
        origin_date = origin.end_time.date().isoformat()
        target_date = (origin + 1).end_time.date().isoformat()
        seasonal_date = (origin - 3).end_time.date().isoformat()
        known = versions[versions.info_public_date.le(origin_date) & versions.period_end.le(origin_date)]
        known = known.sort_values("info_public_date").drop_duplicates(["period_end", "product_basis"], keep="last")
        for product, group in known.groupby("product_basis"):
            seasonal = group[group.period_end.eq(seasonal_date)]
            outcome = actual[actual.product_basis.eq(product) & actual.period_end.eq(target_date)]
            if len(seasonal) != 1 or len(outcome) != 1:
                continue  # Common support: all three naive forecasts must exist.
            last = group.sort_values("period_end").iloc[-1]
            for method, value in [("latest_available_persistence", last.value),
                                  ("seasonal_previous_year", seasonal.iloc[0].value),
                                  ("available_history_mean", group.value.mean())]:
                selected = group if method == "available_history_mean" else (
                    seasonal if method == "seasonal_previous_year" else group[group.period_end.eq(last.period_end)])
                predictions.append(dict(product_basis=product, origin=origin_date,
                                        target=target_date, method=method, prediction=float(value),
                                        actual=float(outcome.iloc[0].value),
                                        max_training_public_date=selected.info_public_date.max(),
                                        max_training_period_end=selected.period_end.max(),
                                        training_sources=";".join(sorted(selected.source_id.unique())),
                                        outcome_source=outcome.iloc[0].source_id,
                                        outcome_public_date=outcome.iloc[0].info_public_date,
                                        native_unit="reported oxide/product-family tonnes"))
    return pd.DataFrame(predictions)
