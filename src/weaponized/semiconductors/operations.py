"""SMIC issuer-native scale measurements, not target capability/access scores.

Shipments are not wafers out. A reported monthly capacity rate is not estimated
quarterly capacity, and wafer-revenue shares are not physical output shares.
The source's equivalent-wafer definition is versioned rather than converted.
"""
from datetime import datetime
import math
import re

import pandas as pd

from weaponized.io.original_text import normalize_evidence


def _one(pattern, text, flags=0):
    matches=list(re.finditer(pattern,text,flags))
    if len(matches)!=1:
        raise ValueError(f"Expected one named source row/phrase: {pattern}; found {len(matches)}")
    return matches[0]


def _line(page, label):
    match=_one(r"^\s*"+label+r"[ \t]+([^\n]+)$",page,re.M)
    return match[1].split(),normalize_evidence(match[0])


def _numeric(token, percent=False):
    pattern=r"\d+(?:\.\d+)?%" if percent else r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    if not re.fullmatch(pattern,token):
        raise ValueError("Unregistered numeric/missing source token")
    number=float(token.replace(",","").rstrip("%"))
    if not math.isfinite(number) or number<0 or (percent and number>100):
        raise ValueError("Source quantity outside native domain")
    return number


def _header(page, year, interleaved=False):
    q=[f"4Q{year%100:02}",f"3Q{year%100:02}",f"4Q{(year-1)%100:02}"]
    middle=r"\s+QoQ\s+" if interleaved else r"\s+"
    pattern=re.escape(q[0])+r"\s+"+re.escape(q[1])+middle+re.escape(q[2])
    if interleaved:pattern+=r"\s+YoY"
    match=re.search(pattern,page)
    if not match:
        raise ValueError("Quarterly table header missing or incorrectly ordered")
    return q,normalize_evidence(match[0])


def parse_smic_operations(text, spec):
    year=spec["report_year"]
    pages=text.split("\f")
    public=datetime.strptime(spec["info_public_date"],"%Y-%m-%d")
    if public.date().isoformat()>"2026-10-11":
        raise ValueError("Post-freeze release")
    display=public.strftime("%B %-d, %Y")
    if display not in normalize_evidence(pages[0]):
        raise ValueError("Issuer release clock not supported on PDF page 1")
    if not re.search(r"(?:December|DECEMBER) 31,\s*"+str(year),pages[0]):
        raise ValueError("Release reporting year not supported on PDF page 1")
    rows=[]
    basis="standard_logic_8inch_equivalent" if year>=2024 else "generic_8inch_equivalent"

    def emit(variable, token, quarter, page_number, quote, header, unit, product, frequency="quarter", percent=False):
        period=str(pd.Period(quarter,freq="Q").end_time.date()) if frequency=="quarter" else f"{year}-12-31"
        rows.append(dict(variable=variable,value=_numeric(token,percent),source_cell_token=token,
                         period_end=period,period_frequency=frequency,native_unit=unit,product_basis=product,
                         source_definition_version=("explicit_8inch_equivalent_wafers_out" if year<2024 else "total_wafers_out_basis_unspecified_in_note") if variable=="capacity_utilization" else product,
                         measurement_timing=("monthly_rate_reported_for_quarter" if variable=="monthly_capacity" else
                                             "year_end_monthly_rate_summary" if variable=="rounded_yearend_monthly_capacity" else
                                             "issuer_annual_or_annualized_summary" if variable=="annual_utilization_summary" else
                                             "ratio_over_estimated_quarter" if variable=="capacity_utilization" else
                                             "quarter_revenue_share" if variable.endswith("revenue_share") else "quarter_total"),
                         pdf_page=page_number,quote=quote,header_quote=header,
                         locator=f"PDF page {page_number}; named row/phrase {variable}; {period}; exact period header retained"))

    op_number=spec["operations_page"]
    op_page=pages[op_number-1]
    op=op_page.split("Shipment and Utilization",1)[1]
    _,header=_header(op,year,True)
    periods=[f"{year}Q4",f"{year}Q3",f"{year-1}Q4"]
    required="Based on standard logic 8-inch equivalent" if year>=2024 else "8’’ equivalent wafers out"
    if required not in normalize_evidence(op):
        raise ValueError("Source equivalent-wafer definition missing")
    for variable,label,positions,unit,product,percent in [
        ("wafer_shipments",r"Wafer shipments(?:\(1\))?",[0,1,3],"reported_equivalent_wafers",basis,False),
        ("capacity_utilization",r"Utilization rate\([12]\)",[0,1,2],"percent","wafers_out_over_estimated_quarterly_capacity",True),
    ]:
        tokens,quote=_line(op,label)
        if len(tokens)!=(5 if variable=="wafer_shipments" else 3):
            raise ValueError("Operating table cells do not match the named header")
        for period,pos in zip(periods,positions):emit(variable,tokens[pos],period,op_number,quote,header,unit,product,percent=percent)
    cap=_one(r"Monthly capacity increased to (?P<current>[\d,]+).*?4Q"+f"{year%100:02}"+r".*?from (?P<previous>[\d,]+).*?3Q"+f"{year%100:02}"+r"\.",normalize_evidence(op_page))
    for key,period in [("current",f"{year}Q4"),("previous",f"{year}Q3")]:
        emit("monthly_capacity",cap[key],period,op_number,cap[0],"quarter labels in capacity sentence",
             "reported_equivalent_wafers_per_month",basis,frequency="quarter")

    revenue_number=spec["revenue_page"]
    rev=pages[revenue_number-1]
    if "Amounts in US$ thousands" not in normalize_evidence(rev):
        raise ValueError("Monetary table unit absent")
    _,header=_header(rev,year,True)
    tokens,quote=_line(rev,r"Revenue")
    if len(tokens)!=5:raise ValueError("Revenue row does not match the named header")
    for period,pos in zip(periods,[0,1,3]):
        emit("total_revenue",tokens[pos],period,revenue_number,quote,header,"USD_thousands","consolidated_total_revenue")

    mix_number=spec["mix_page"]
    mix=pages[mix_number-1]
    service=mix.split("By Service Type",1)[1].split("Wafer Revenue Analysis",1)[0]
    _,header=_header(service,year)
    for variable,label,product in [("wafer_service_revenue_share","Wafers","share_of_total_revenue"),
                                    ("other_service_revenue_share","Others","share_of_total_revenue")]:
        tokens,quote=_line(service,label)
        if len(tokens)!=3:raise ValueError("Service share row/header mismatch")
        for period,token in zip(periods,tokens):emit(variable,token,period,mix_number,quote,header,"percent",product,percent=True)
    # FY2025 prints the size header immediately before 'By Size', not after it.
    size=mix[mix.index("By Size"):]
    header_region=mix[max(0,mix.index("By Size")-180):mix.index("By Size")+180]
    _,header=_header(header_region,year)
    for inches in [8,12]:
        tokens,quote=_line(size,str(inches)+"” wafers")
        if len(tokens)!=3:raise ValueError("Wafer size revenue row/header mismatch")
        for period,token in zip(periods,tokens):
            emit(f"wafer_{inches}inch_revenue_share",token,period,mix_number,quote,header,"percent","share_of_wafer_revenue_not_physical_output",percent=True)

    rd_number=spec["rd_page"]
    rd=pages[rd_number-1]
    _,header=_header(rd,year,True)
    tokens,quote=_line(rd,"Research and development expenses")
    if len(tokens)!=5:raise ValueError("R&D row/header mismatch")
    for period,pos in zip(periods,[0,1,3]):
        emit("rd_expense",tokens[pos],period,rd_number,quote,header,"USD_thousands","nominal_reported_R_and_D_input")
    capex_number=spec["capex_page"]
    capex=normalize_evidence(pages[capex_number-1])
    c=_one(r"Capital expenditure was \$\s?(?P<current>[\d,.]+) million in 4Q"+f"{year%100:02}"+r", compared to \$(?P<previous>[\d,.]+) million in 3Q"+f"{year%100:02}"+r"\.",capex)
    for key,period in [("current",f"{year}Q4"),("previous",f"{year}Q3")]:
        emit("capital_expenditure",c[key],period,capex_number,c[0],"quarter labels in expenditure sentence","USD_millions","nominal_reported_capital_expenditure_input")
    for item in spec["annual_summary"]:
        summary=normalize_evidence(pages[item["pdf_page"]-1]);m=_one(item["pattern"],summary)
        token=m["value"]
        if _numeric(token,item["variable"]=="annual_utilization_summary")!=item["value"]:
            raise ValueError("Curated annual summary value differs from original named quantity")
        emit(item["variable"],token,None,item["pdf_page"],m[0],"annual management summary; exact wording retained",item["native_unit"],
             basis if item["variable"]=="rounded_yearend_monthly_capacity" else "issuer_annual_utilization_summary",frequency="annual_summary",percent=item["variable"]=="annual_utilization_summary")
    if len(rows)!=30:
        raise ValueError("Unexpected SMIC source-native cell coverage")
    return rows


def smic_definition_quotes(text,spec):
    pages=text.split("\f");year=spec["report_year"]
    op=normalize_evidence(pages[spec["operations_page"]-1].split("Shipment and Utilization",1)[1])
    utilization=_one(r"\([12]\) Based on total .*?wafers out divided by estimated total quarterly capacity\.",op)[0]
    if year>=2024:
        shipment=_one(r"\(1\) Based on standard logic 8-inch equivalent(?: wafers)?\.?",op)[0]
    else:
        shipment=_one(r"8” equivalent wafers\s+4Q"+f"{year%100:02}"+r"\s+3Q"+f"{year%100:02}"+r"\s+QoQ\s+4Q"+f"{(year-1)%100:02}"+r"\s+YoY",op)[0]
    mix=normalize_evidence(pages[spec["mix_page"]-1])
    size=mix[mix.index("Wafer Revenue Analysis"):]
    end=_one(r"12” wafers\s+[\d.]+%\s+[\d.]+%\s+[\d.]+%",size).end()
    return [dict(definition="shipment_equivalent_basis",quote=shipment,pdf_page=spec["operations_page"]),
            dict(definition="utilization_denominator",quote=utilization,pdf_page=spec["operations_page"]),
            dict(definition="wafer_size_revenue_denominator",quote=size[:end],pdf_page=spec["mix_page"])]


def asof_operations(frame, origin, freeze="2026-10-11"):
    if origin>freeze:raise ValueError("Origin exceeds research freeze")
    known=frame[frame.info_public_date.le(origin) & frame.period_end.le(origin)]
    return known.sort_values(["info_public_date","source_id"]).drop_duplicates(["variable","period_end","period_frequency"],keep="last")


def wafer_revenue_bridge(total_revenue_usd, wafer_share_percent, shipments):
    if any(not math.isfinite(x) for x in [total_revenue_usd,wafer_share_percent,shipments]) or total_revenue_usd<=0 or shipments<=0 or not 0<wafer_share_percent<=100:
        raise ValueError("Bridge inputs must be finite, positive and in their native domains")
    wafer_revenue=total_revenue_usd*wafer_share_percent/100
    return dict(wafer_attributed_revenue_usd=wafer_revenue,
                nominal_wafer_revenue_per_reported_equivalent_shipment=wafer_revenue/shipments,
                quality_adjusted_price=None,advanced_node_yield=None,domestic_capability_z=None,
                foreign_access_f=None,combined_availability_a=None,
                interpretation="Descriptive reported-revenue ratio; mix, recognition timing, cost, quality and target performance not separated")


def revenue_decomposition(current, previous):
    fields=["wafer_attributed_revenue_usd","shipments","nominal_wafer_revenue_per_reported_equivalent_shipment"]
    if any(not math.isfinite(row[k]) or row[k]<=0 for row in [current,previous] for k in fields):
        raise ValueError("Strictly positive finite source-native quantities required")
    revenue=math.log(current[fields[0]]/previous[fields[0]])
    quantity=math.log(current[fields[1]]/previous[fields[1]])
    ratio=math.log(current[fields[2]]/previous[fields[2]])
    residual=revenue-quantity-ratio
    return dict(log_wafer_revenue_change=revenue,log_shipments_change=quantity,log_revenue_per_equivalent_shipment_change=ratio,
                identity_residual=residual,passed=abs(residual)<1e-12,
                causal_effect=None,technological_substitution=None,
                classification="nominal_accounting_identity_not_quality_adjusted_price_or_causal_estimate")
