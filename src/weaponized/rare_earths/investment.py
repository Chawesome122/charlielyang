"""Publication-vintaged consolidated cash investment inputs from SEC facts.

Reported durations can overlap. Quarterly, year-to-date and annual observations
remain different objects and must never be summed as a single expenditure panel.
"""
import math

import pandas as pd

from weaponized.io.schemas import Claim

TAG = "PaymentsToAcquirePropertyPlantAndEquipment"


def extract_cash_ppe_versions(payload, source_id, source_sha256, freeze="2026-10-11"):
    facts = payload["facts"]["us-gaap"][TAG]["units"]["USD"]
    rows = []
    for i, fact in enumerate(facts):
        if fact.get("form") not in {"10-K", "10-Q", "10-K/A", "10-Q/A"}:
            continue
        # Do not mix the pre-combination SPAC/predecessor periods into this
        # consolidated operating-company input series.
        if not fact.get("start") or fact["start"] < "2021-01-01" or fact["filed"] > freeze:
            continue
        if fact["end"] > fact["filed"] or fact["end"] < fact["start"] or not math.isfinite(fact["val"]):
            raise ValueError("Invalid cash-flow period, public clock or financial value")
        observation = f"MP-PPE-CASH-{fact['start']}-{fact['end']}"
        row = dict(observation_id=observation, record_version_id=observation+"-"+fact["accn"],
                   entity_id="MP_Materials_consolidated", variable="reported_cash_ppe_payments",
                   value=fact["val"], native_unit="USD nominal cash payments over the stated duration",
                   product_basis="consolidated property plant and equipment cash payments; not physical output",
                   valid_date=fact["end"], info_public_date=fact["filed"], source_id=source_id,
                   source_sha256=source_sha256,
                   locator=f"$.facts.us-gaap.{TAG}.units.USD[{i}]",
                   evidence_class="empirical", event_kind="observed")
        Claim(**row)
        rows.append(row | dict(period_start=fact["start"], period_end=fact["end"],
                               accession_number=fact["accn"], form=fact["form"],
                               report_fiscal_year=fact.get("fy"), report_fiscal_period=fact.get("fp"),
                               source_frame=fact.get("frame"), source_array_index=i,
                               scope="company-wide; no project/stage allocation or causal response identified",
                               source_clock_basis="original filing date in archived SEC companyfacts; original XBRL contexts not independently reconciled"))
    data = pd.DataFrame(rows)
    if not data.empty and data.record_version_id.duplicated().any():
        raise ValueError("Repeated/conflicting fact contexts require original XBRL adjudication")
    return data.sort_values(["period_start", "period_end", "info_public_date"]).reset_index(drop=True)
