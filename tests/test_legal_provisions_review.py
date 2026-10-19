"""Independent checks of semantic associations in the original issued rules.

These supplement quote equality: the correct number or paragraph can still be
assigned to the wrong variable, certification label, or compliance instruction.
"""
from datetime import datetime
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[1]
BOOK=json.loads((ROOT/"codebooks/legal_provisions.json").read_text())
CLAIMS={row["claim_id"]:row for row in BOOK["clauses"]}


def original(document):
    path=next((ROOT/"data/raw/semiconductors").glob(f"SC-FR-{document}-TEXT-*.xml"))
    return ET.fromstring(path.read_bytes())


def normalized(node):
    return " ".join(" ".join(node.itertext()).split())


def original_quote(claim):
    root=original(claim["document_number"])
    return " ".join(normalized(root.find(e["xpath"])) for e in claim["evidence"])


def named_review_bounds(claim):
    """Parse the two named 2026 quantities independently of curated bounds."""
    quote=original_quote(claim).replace(",","")
    result={}
    for variable,marker in [("total_processing_performance",r"\bTPP"),
                            ("total_dram_bandwidth",r"`total DRAM bandwidth'")]:
        match=re.search(marker+r" \(as defined.*?\) less than (\d+)",quote)
        assert match is not None
        result[variable]=("<",float(match[1]))
    return result


def structured_bounds(claim):
    return {bound["variable"]:(bound["operator"],float(bound["value"]))
            for bound in claim["parameter_bounds"]}


def test_named_2026_parameters_are_not_interchangeable_nearby_numbers():
    claim=CLAIMS["LP-2026-review"]
    expected=named_review_bounds(claim)
    assert structured_bounds(claim)==expected
    # All numbers/operators remain in the quote under this incorrect recoding.
    swapped=claim|{"parameter_bounds":[dict(bound,variable=("total_dram_bandwidth" if bound["variable"]=="total_processing_performance" else "total_processing_performance")) for bound in claim["parameter_bounds"]]}
    assert structured_bounds(swapped)!=expected


def test_all_nine_certifications_match_exact_original_roman_groups_in_order():
    root=original("2026-00789")
    section=root.find("./SUPLINF[1]/REGTEXT[7]")
    groups={}
    current=None
    active=False
    for node in section.findall("P"):
        text=normalized(node)
        if text.startswith("(1) Certification."):
            active=True
            continue
        if text.startswith("Notes to paragraph (dd)(1):"):
            break
        if not active:
            continue
        match=re.match(r"^\(([ivx]+)\)",text)
        if match:
            current=match[1]
            groups[current]=[]
        assert current is not None
        groups[current].append(text)
    names=[("i","US-shipments"),("ii","US-supply"),("iii","50-percent"),
           ("iv","enduses"),("v","KYC"),("vi","remote-users"),
           ("vii","IaaS"),("viii","security"),("ix","every-shipment")]
    assert list(groups)==[roman for roman,_ in names]
    for roman,name in names:
        claim=CLAIMS["LP-2026-"+name]
        assert claim["legal_locator"].endswith(f"(dd)(1)({roman})")
        coded=[normalized(root.find(e["xpath"])) for e in claim["evidence"]]
        assert coded==groups[roman]


def test_effect_and_compliance_dates_follow_original_dates_elements():
    for document in BOOK["documents"]:
        root=original(document["document_number"])
        dates=normalized(root.find(document["dates_xpath"]))
        date_match=re.search(r"(?:is effective|effective date of this rule is) ([A-Z][a-z]+ \d{1,2}, \d{4})",dates)
        assert date_match
        effective=datetime.strptime(date_match[1],"%B %d, %Y").date().isoformat()
        delayed=set()
        delayed_date=None
        if document["document_number"]=="2024-28270":
            match=re.search(r"instructions ([\d, and]+) \(ECCNs.*?have a compliance date of ([A-Z][a-z]+ \d{1,2}, \d{4})",dates)
            assert match
            delayed={int(number) for number in re.findall(r"\d+",match[1])}
            delayed_date=datetime.strptime(match[2],"%B %d, %Y").date().isoformat()
        for claim in BOOK["clauses"]:
            if claim["document_number"]!=document["document_number"]:
                continue
            assert claim["effective_date"]==effective
            expected=delayed_date if claim["amendatory_instruction"] in delayed else effective
            assert claim["compliance_date"]==expected


@pytest.mark.parametrize("claim_id,variable,operator,pattern",[
    ("LP-2024-hbm-threshold","memory_bandwidth_density",">",r"memory bandwidth density' greater than (\d+(?:\.\d+)?)"),
    ("LP-2024-hbm-exception-threshold","memory_bandwidth_density","<",r"memory bandwidth density less than (\d+(?:\.\d+)?)"),
])
def test_hbm_signs_and_values_are_bound_to_the_density_phrase(claim_id,variable,operator,pattern):
    claim=CLAIMS[claim_id]
    match=re.search(pattern,original_quote(claim))
    assert match
    assert structured_bounds(claim)=={variable:(operator,float(match[1]))}
