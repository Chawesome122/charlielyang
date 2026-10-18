from weaponized.io.vintages import select_asof
from weaponized.rare_earths.investment import TAG, extract_cash_ppe_versions


def payload(rows):
    return {"facts":{"us-gaap":{TAG:{"units":{"USD":rows}}}}}


def fact(start, end, value, filed, accession):
    return dict(start=start, end=end, val=value, filed=filed, accn=accession, form="10-Q", fy=2026, fp="Q2")


def test_comparative_reporting_year_does_not_replace_observation_period_or_public_clock():
    rows = [fact("2025-01-01", "2025-06-30", 10, "2025-08-01", "a"),
            fact("2025-01-01", "2025-06-30", 11, "2026-08-01", "b"),
            fact("2025-01-01", "2025-06-30", 999, "2026-10-12", "future")]
    data = extract_cash_ppe_versions(payload(rows), "source", "a"*64)
    assert len(data) == 2
    assert select_asof(data, "2025-12-31").iloc[0].value == 10
    assert select_asof(data, "2026-10-11").iloc[0].value == 11
    assert data.period_end.eq("2025-06-30").all()


def test_overlapping_cashflow_durations_are_not_deduplicated_by_end_date():
    rows = [fact("2026-01-01", "2026-06-30", 30, "2026-08-01", "a"),
            fact("2026-04-01", "2026-06-30", 20, "2026-08-01", "a")]
    data = extract_cash_ppe_versions(payload(rows), "source", "a"*64)
    assert select_asof(data, "2026-10-11").observation_id.nunique() == 2
    zero = extract_cash_ppe_versions(payload([fact("2026-01-01", "2026-03-31", 0, "2026-05-01", "zero")]), "source", "a"*64)
    assert zero.iloc[0].value == 0
