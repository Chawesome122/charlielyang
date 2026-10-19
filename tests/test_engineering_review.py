"""Independent review of archived MP assumption contexts and oxide accounting.

Fresh original HTML and Decimal arithmetic are used without the engineering
extractor or its grouped_oxide_constraint implementation.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def original_text(source_id):
    source = json.loads((ROOT / "data/processed/rare_earths/source_index.json").read_text())[source_id]
    payload = (ROOT / source["archive_path"]).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == source["sha256"]
    return " ".join(BeautifulSoup(payload, "html.parser").get_text(" ", strip=True).split())


def test_both_originals_separate_resource_and_reserve_recovery_assumptions():
    expected = {"RE-MP-10K2024": [("75.0", "11.5"), ("75.0", "11.5")],
                "RE-MP-10K2025": [("75.0", "11.5"), ("74.9", "8.9")]}
    for source_id, expected_contexts in expected.items():
        text = original_text(source_id)
        # Separate full original sections before locating the numerical statement.
        heads = list(re.finditer(r"Mineral (Resources|Reserves) As of December 31, \d{4}, SRK", text))
        assert [m[1] for m in heads] == ["Resources", "Reserves"]
        for i, ((la, ce), heading) in enumerate(zip(expected_contexts, heads)):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            section = text[heading.end():end]
            matches = re.findall(r"Overall recoveries at the onsite separations plant as applied to concentrate containing on average (\d+)% TREO are: PrNd Oxide \(([\d.]+)%\), SEG\+ Precipitate \(([\d.]+)%\), La Carbonate \(([\d.]+)%\) and Ce Chloride \(([\d.]+)%\)\.", section)
            assert matches == [("60", "89.7", "97.9", la, ce)]


def test_independent_decimal_group_accounting_matches_all_four_conditional_rows():
    # This is a calculation conditional on disclosed issuer model assumptions,
    # not an independent assay or empirical operating yield measurement.
    grade = Decimal("60") / 100
    grouped_share = Decimal("15.7") / 100
    recovery = Decimal("89.7") / 100
    incoming = grade * grouped_share
    recovered = incoming * recovery
    unrecovered = incoming - recovered
    assert incoming == Decimal("0.0942")
    assert recovered == Decimal("0.0844974")
    assert unrecovered == Decimal("0.0097026")
    assert incoming == recovered + unrecovered
    rows = pd.read_csv(ROOT / "data/processed/engineering_inputs/conditional_oxide_constraints.csv")
    assert len(rows) == 4
    assert set(rows["product"]) == {"PrNd"}
    assert set(rows["input_basis"]) == {"tonne_native_concentrate"}
    assert set(rows["output_basis"]) == {"tonne_REO_equivalent"}
    for record in rows.to_dict("records"):
        assert record["recovered_product_REO_equivalent_per_native_tonne"] == pytest.approx(float(recovered))
        assert record["unrecovered_product_REO_equivalent_per_native_tonne"] == pytest.approx(float(unrecovered))
        assert not record["observed_operating_yield"]
        assert not record["full_recipe_identified"]
    for field in ["annual_output", "finite_available_feed", "physical_sale_product_mass", "elemental_Nd_Pr_split", "China_free_service"]:
        assert rows[field].isna().all()


def test_hree_omission_is_resource_scope_and_never_a_zero_flow():
    text = original_text("RE-MP-10K2025")
    sentence = ("While other REE, often referred to as HREE, are present in the deposit, "
                "they are not accounted for in this estimate due to historic data limitations.")
    assert sentence in text
    position = text.index(sentence)
    previous = list(re.finditer(r"Mineral (Resources|Reserves) As of December 31, \d{4}, SRK", text[:position]))
    assert previous[-1][1] == "Resources"
    assert "The mineral resource statement reported herein only includes the REE cerium, lanthanum, neodymium, praseodymium, and samarium" in text[position - 300:position]
    observations = pd.read_csv(ROOT / "data/processed/engineering_inputs/observations.csv")
    hree = observations[observations.variable.eq("HREE_resource_accounting")].iloc[0]
    assert hree["value"] == "not accounted for in this estimate"
    assert hree["classification"] == "unknown_quantity"
    assert not hree["actual_industrial_flow_identified"]


def test_planning_inputs_and_source_native_group_names_remain_separate_from_flows():
    rows = pd.read_csv(ROOT / "data/processed/engineering_inputs/observations.csv")
    numeric = pd.to_numeric(rows["value"], errors="coerce").notna()
    assert numeric.sum() == 28
    assert set(rows.loc[numeric, "evidence_class"]) == {"calibrated"}
    assert set(rows.loc[~numeric, "evidence_class"]) == {"empirical"}
    assert not rows.actual_industrial_flow_identified.any()
    assert not rows.historical_byte_vintage_certified.any()
    distribution = rows[rows.variable.eq("concentrate_REO_distribution")]
    assert set(distribution.product_basis) == {"PrNd", "SEG+", "Lanthanum", "Cerium"}
    for source_id, group in distribution.groupby("source_id"):
        assert sum(Decimal(str(x)) for x in group.value) == Decimal("100.0")
        assert "PrNd (15.7%)" in original_text(source_id)
    # No fabricated Nd, Pr, Dy or Tb split is introduced by this grouped basis.
    assert not rows.product_basis.isin(["Nd", "Pr", "Dy", "Tb"]).any()
