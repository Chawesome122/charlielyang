"""Exact-link clocks, native measurement bases and financing identity guards."""
import json
from pathlib import Path

import pandas as pd
import pytest

from weaponized.io.publication import linked_publication_clock
from weaponized.rare_earths.finance import cash_reconciliation, facility_reconciliation, planned_capacity_retention

ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://issuer.example/report/"
PDF = "https://issuer.example/files/report.pdf"


def article(kind="Article", main=PAGE, published="2026-03-27T09:55:03+00:00", link_inside=True):
    node = {"@type":kind, "mainEntityOfPage":{"@id":main}, "datePublished":published,
            "dateModified":"2026-09-01T00:00:00Z"}
    link = '<a href="/files/report.pdf">Report</a>'
    return '<script type="application/ld+json">'+json.dumps(node)+'</script><article>'+(link if link_inside else '')+'</article>'+('' if link_inside else link)


def test_exact_card_cannot_borrow_an_adjacent_documents_date():
    html = '<a href="/files/other.pdf"><span class="document-date">01 Jan 2020</span></a><a href="/files/report.pdf"><span class="document-date">19 Aug 2026</span></a>'
    assert linked_publication_clock(html, PAGE, PDF, "dated_link_card")["info_public_date"] == "2026-08-19"
    html = html.replace('<span class="document-date">19 Aug 2026</span>', 'undated report')
    with pytest.raises(ValueError):
        linked_publication_clock(html, PAGE, PDF, "dated_link_card")


def test_conflicting_cards_and_post_freeze_dates_are_rejected():
    for dates in [["18 Aug 2026", "19 Aug 2026"], ["12 Oct 2026"]]:
        html = ''.join('<a href="/files/report.pdf"><span class="document-date">'+d+'</span></a>' for d in dates)
        with pytest.raises(ValueError):
            linked_publication_clock(html, PAGE, PDF, "dated_link_card")


def test_article_publication_is_distinct_from_page_modification():
    clock = linked_publication_clock(article(), PAGE, PDF, "article_jsonld")
    assert clock["info_public_date"] == "2026-03-27"
    assert not clock["historical_byte_vintage_certified"]


@pytest.mark.parametrize("html", [article(kind="WebPage"), article(main="https://issuer.example/other/"), article(main=""), article(link_inside=False), article()+"<article>related post</article>"])
def test_page_or_unrelated_article_dates_cannot_become_report_clocks(html):
    with pytest.raises(ValueError):
        linked_publication_clock(html, PAGE, PDF, "article_jsonld")


def test_cash_additions_working_capital_and_cash_payments_remain_different():
    good = cash_reconciliation(-10773620, -225102, -10998722, -4999892, -15998614)
    assert good["passed"] and not good["physical_output_inferred"]
    assert not cash_reconciliation(-10773620, -225102, -10998722, 0, -15998614)["passed"]


def test_undrawn_and_separate_overrun_are_not_cash_or_base_facility():
    assert facility_reconciliation(1650, 897.5, 752.5)["passed"]
    assert not facility_reconciliation(1725, 897.5, 752.5)["passed"]
    assert not facility_reconciliation(1650, 897.5, 752.5)["undrawn_is_cash"]


@pytest.mark.parametrize("bad", [-1, float("inf"), float("nan")])
def test_invalid_facility_balances_rejected(bad):
    with pytest.raises(ValueError):
        facility_reconciliation(1650, bad, 752.5)


def test_feedstock_comparison_does_not_identify_network_service_or_annual_output():
    args = dict(product_base="NdPr oxide", product_expanded="NdPr oxide", unit_base="native prospective tonnes", unit_expanded="native prospective tonnes")
    result = planned_capacity_retention(3500, 5500, **args)
    assert result["stockpile_only_to_expanded_ratio"] == pytest.approx(7/11)
    assert result["annual_output_estimate"] is None and result["china_free_service"] is None
    with pytest.raises(ValueError):
        planned_capacity_retention(3500, 5500, **(args | {"product_expanded":"DyTb oxide"}))
    with pytest.raises(ValueError):
        planned_capacity_retention(3500, 5500, **(args | {"unit_expanded":"tonnes/year"}))


def test_actual_new_claims_preserve_products_signs_currency_and_public_clocks():
    data = pd.read_csv(ROOT/"data/processed/finance_material/observations.csv")
    assert data.record_version_id.is_unique
    products = data[data.variable.eq("prospective_product_quantity")]
    assert len(products) == 4 and products.product_basis.nunique() == 2
    cash = data[data.variable.eq("cash_ppe_intangibles_payments")]
    assert sorted(pd.to_numeric(cash.value)) == [-15998614, -4369954]
    assert cash.info_public_date.eq("2026-03-27").all()
    assert not data.historical_byte_vintage_certified.any()
    clocks = pd.read_csv(ROOT/"data/processed/finance_material/publication_clock_audit.csv")
    assert clocks.status.eq("RESOLVED").sum() == 4
    assert clocks[clocks.status.eq("UNRESOLVED")].info_public_date.isna().all()
