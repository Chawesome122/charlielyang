"""2026 quarterly extension of issuer-native SMIC measurement contracts."""
from datetime import datetime
import re

import pandas as pd
from weaponized.io.supplied_evidence import one_match
from weaponized.semiconductors.operations import _numeric


def parse_quarterly_release(pages, spec, source):
    if source['info_public_date']>'2026-10-11':raise ValueError('Post-freeze release')
    year, quarter = spec["year"], spec["quarter"]
    period = pd.Period(f"{year}Q{quarter}", freq="Q")
    display = datetime.strptime(source["info_public_date"], "%Y-%m-%d").strftime("%B %-d, %Y")
    one_match(r"Shanghai, China –\s*"+re.escape(display)+r" – Semiconductor Manufacturing International Corporation", pages[0])
    if period.end_time.strftime("%B %-d, %Y").upper() not in pages[0]:
        raise ValueError("Source reporting period disagrees with registered quarter")
    labels = [f"{p.quarter}Q{p.year%100:02d}" for p in [period,period-1,period-4]]
    periods = [str(p.end_time.date()) for p in [period,period-1,period-4]]
    def header(page, interleaved):
        s = (labels[0]+r" "+labels[1]+(r" QoQ " if interleaved else " ")+labels[2]+(r" YoY" if interleaved else ""))
        # Several financial subsections have the identical header: their row
        # locators and page are explicit; no arbitrary first-row selection.
        if not re.search(s, page):raise ValueError("Quarter header missing or reordered")
        return re.search(s, page)[0]
    op = pages[4]
    for definition in ["Based on standard logic 8-inch equivalent wafers.",
                       "Based on total wafers out divided by estimated total quarterly capacity."]:
        if definition not in op:raise ValueError("Equivalent/denominator source definition absent")
    rows=[]
    def emit(variable, token, end, page, quote, head, unit, basis, percent=False):
        rows.append(dict(observation_id=f"SMIC:{variable}:{end}",record_version_id=f"{source['source_id']}:{variable}:{end}",
                         source_id=source["source_id"],source_sha256=source["sha256"],source_url=source["source_url"],
                         archive_path=source["archive_path"],info_public_date=source["info_public_date"],
                         variable=variable,period_end=end,report_period_end=periods[0],
                         value=_numeric(token,percent),source_cell_token=token,native_unit=unit,product_basis=basis,
                         quote=quote,header_quote=head,pdf_page=page,locator=f"PDF page {page}; {variable}; {end}; exact quarter header",
                         historical_byte_vintage_certified=False,target_capability_identified=False,
                         foreign_access_identified=False,causal_effect_identified=False))
    # Keep physical-rate, flow, share, monetary and denominator objects separate.
    # The source row parser needs newlines. Recover row boundaries by named
    # section captures with explicit token counts, not arbitrary digit searches.
    n=r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    pct=r"-?\d+(?:\.\d+)?%"
    rowspecs=[("total_revenue","Revenue",4,"USD_thousands","consolidated_total_revenue",False,True),
              ("rd_expense","Research and development expenses",6,"USD_thousands","nominal_R_and_D_input",False,True),
              ("wafer_shipments",r"Wafer shipments\(1\)",5,"reported_equivalent_wafers","standard_logic_8inch_equivalent",False,True),
              ("capacity_utilization",r"Utilization rate\(2\)",5,"percent","wafers_out_over_estimated_quarterly_capacity",True,False),
              ("wafer_service_revenue_share","Wafers",5,"percent","share_of_total_revenue",True,False),
              ("other_service_revenue_share","Others",5,"percent","share_of_total_revenue",True,False),
              ("wafer_8inch_revenue_share","8” wafers",5,"percent","share_of_wafer_revenue_not_physical_output",True,False),
              ("wafer_12inch_revenue_share","12” wafers",5,"percent","share_of_wafer_revenue_not_physical_output",True,False)]
    for var,label,page,unit,basis,is_percent,interleaved in rowspecs:
        text=pages[page-1];tok=pct if is_percent else n
        if var=='rd_expense':text=text.split('Operating Expenses',1)[1].split('Other Income, Net',1)[0]
        elif var in ['wafer_shipments','capacity_utilization']:text=text.split('Shipment and Utilization',1)[1].split('Notes:',1)[0]
        elif var in ['wafer_service_revenue_share','other_service_revenue_share']:text=text.split('By Service Type',1)[1].split('Wafer Revenue Analysis',1)[0]
        elif var in ['wafer_8inch_revenue_share','wafer_12inch_revenue_share']:
            # This source prints the size header immediately before By Size.
            start=text.index('By Size');text=text[max(0,start-30):].split('Capacity',1)[0]
        pattern=label+r" (?P<c>"+tok+r") (?P<p>"+tok+r") "+((pct+r" ") if interleaved else "")+r"(?P<y>"+tok+r")"+((" "+pct) if interleaved else "")
        m=one_match(pattern,text);h=header(text,interleaved or var=='capacity_utilization')
        for group,end in zip(["c","p","y"],periods):emit(var,m[group],end,page,m[0],h,unit,basis,is_percent)
    m=one_match(r"Monthly capacity increased to (?P<c>"+n+r") standard logic 8-inch equivalent wafers in "+labels[0]+r" from (?P<p>"+n+r") standard logic 8-inch equivalent wafers in "+labels[1]+r"\.",op)
    for group,end in zip(["c","p"],periods[:2]):emit("monthly_capacity",m[group],end,5,m[0],"quarters named in sentence","reported_equivalent_wafers_per_month","standard_logic_8inch_equivalent")
    m=one_match(r"Capital expenditure was \$(?P<c>"+n+r") million in "+labels[0]+r", compared to \$(?P<p>"+n+r") million in "+labels[1]+r"\.",op)
    for group,end in zip(["c","p"],periods[:2]):emit("capital_expenditure",m[group],end,5,m[0],"quarters named in sentence","USD_millions","nominal_capital_expenditure_input")
    if len(rows)!=28:raise ValueError("Unexpected quarterly cell coverage")
    return rows
