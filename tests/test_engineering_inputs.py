"""Engineering-basis and exact original-document association checks."""
import json
from pathlib import Path
import runpy

import pandas as pd
import pytest

from weaponized.rare_earths.engineering import grouped_oxide_constraint, normalized_finite_feed_check

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=runpy.run_path(str(ROOT/"scripts/build_engineering_inputs.py"))
DISTRIBUTION={"PrNd":.157,"SEG+":.018,"Lanthanum":.323,"Cerium":.502}


def constraint(**kwargs):
    return grouped_oxide_constraint(.6,DISTRIBUTION,.897,product="PrNd",
                                     input_basis="tonne_native_concentrate",output_basis="tonne_REO_equivalent",**kwargs)


def test_conditional_recovered_group_accounting_preserves_denominators():
    result=constraint()
    assert result["input_product_REO_equivalent_per_native_tonne"] == pytest.approx(.0942)
    assert result["recovered_product_REO_equivalent_per_native_tonne"] == pytest.approx(.0844974)
    assert result["unrecovered_product_REO_equivalent_per_native_tonne"] == pytest.approx(.0097026)
    assert result["elemental_Nd_Pr_split"] is None
    assert result["physical_sale_product_mass"] is None
    assert result["China_free_service"] is None
    assert result["finite_available_feed"] is None


@pytest.mark.parametrize("bad",[1.01,-.1,float("nan"),float("inf")])
def test_recovery_cannot_create_material(bad):
    with pytest.raises(ValueError):
        grouped_oxide_constraint(.6,DISTRIBUTION,bad,product="PrNd",input_basis="tonne_native_concentrate",output_basis="tonne_REO_equivalent")


def test_joint_shares_cannot_be_four_independent_full_capacity_lines():
    with pytest.raises(ValueError,match="sum to one"):
        grouped_oxide_constraint(.6,{"PrNd":1.,"Ce":1.},.897,product="PrNd",input_basis="tonne_native_concentrate",output_basis="tonne_REO_equivalent")


def test_carbonate_product_mass_is_not_oxide_equivalent_mass():
    with pytest.raises(ValueError,match="bases"):
        grouped_oxide_constraint(.6,DISTRIBUTION,.75,product="Lanthanum",input_basis="tonne_native_concentrate",output_basis="tonne_carbonate_product")


def test_finite_feed_constraints_block_free_material_and_scale_linearly():
    coef=constraint()["recovered_product_REO_equivalent_per_native_tonne"]
    assert normalized_finite_feed_check(coef,0.)["output_upper_bound"] == 0.
    assert normalized_finite_feed_check(coef,.5)["output_upper_bound"] == pytest.approx(coef/2)
    for bad in [-1.,float("inf"),float("nan")]:
        with pytest.raises(ValueError):normalized_finite_feed_check(coef,bad)


def test_matching_another_products_number_does_not_validate_a_claim():
    spec={"variable":"separation_recovery","product_basis":"PrNd Oxide"}
    assert SCRIPT["numerical_value"](spec,"PrNd Oxide (89.7%), La Carbonate (75.0%)") == 89.7
    with pytest.raises(ValueError):SCRIPT["numerical_value"](spec,"La Carbonate (89.7%)")


def test_identical_resource_reserve_quotes_are_bound_to_their_sections():
    specs=json.loads((ROOT/"codebooks/engineering_inputs.json").read_text())["claims"]
    sources=json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    spec=next(s for s in specs if s["source_id"]=="RE-MP-10K2024" and s["variable"]=="separation_recovery" and s["engineering_context"]=="reserve_pit_optimization")
    SCRIPT["original_evidence"](spec,sources,{})
    with pytest.raises(ValueError,match="wrong resource/reserve"):
        SCRIPT["original_evidence"](spec|{"match_ordinal":0},sources,{})


def test_actual_archived_claims_preserve_revised_assumptions_and_unknowns():
    table=pd.read_csv(ROOT/"data/processed/engineering_inputs/observations.csv")
    versions=pd.read_csv(ROOT/"data/processed/engineering_inputs/recovery_assumption_versions.csv")
    assert len(table)==32 and table.record_version_id.is_unique
    assert set(table[table.variable=="separation_recovery"].evidence_class)=={"calibrated"}
    assert not table.historical_byte_vintage_certified.any()
    ce=versions[(versions.engineering_context=="reserve_pit_optimization")&(versions.product_basis=="Ce Chloride")].iloc[0]
    assert (ce.earlier_value,ce.later_value)==(11.5,8.9)
    assert ce.difference_percentage_points==pytest.approx(-2.6)
    resource_ce=versions[(versions.engineering_context=="resource_pit_optimization")&(versions.product_basis=="Ce Chloride")].iloc[0]
    assert resource_ce.difference_percentage_points==0.
    assert set(table[table.classification=="unknown_quantity"].value)=={"not accounted for in this estimate"}
