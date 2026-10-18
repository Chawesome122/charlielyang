import pytest
from weaponized.rare_earths.materials import (annual_to_quarter, contained_elements,
                                            oxide_element_fraction, oxide_to_element)


def test_stoichiometry_and_recovery_are_not_mass_identity():
    fraction = oxide_element_fraction("Nd2O3", "Nd")
    assert fraction == pytest.approx(2 * 144.242 / (2 * 144.242 + 3 * 15.999))
    assert .85 < fraction < .86
    assert oxide_to_element(100, "Nd2O3", "Nd", .9, .95) == pytest.approx(100 * fraction * .9 * .95)
    assert oxide_to_element(100, "Nd2O3", "Nd", .9) < 100


def test_native_oxide_chemistry_cannot_be_guessed():
    with pytest.raises(ValueError):
        oxide_element_fraction("NdPr_mixed_oxide", "Nd")
    with pytest.raises(ValueError):
        oxide_element_fraction("Tb4O7", "Dy")
    with pytest.raises(ValueError):
        oxide_to_element(10, "Nd2O3", "Nd", 1.1)


def test_explicit_annual_calendar_and_composition():
    assert annual_to_quarter(100, convention="uniform_calendar") == 25
    assert annual_to_quarter(100, convention="operating_days", operating_day_fraction=.2) == 20
    with pytest.raises(ValueError):
        annual_to_quarter(100, convention="unknown")
    assert contained_elements(100, {"Nd": .2, "Pr": .05}) == {"Nd": 20, "Pr": 5}
    with pytest.raises(ValueError):
        contained_elements(100, {"Nd": .8, "Pr": .5})
