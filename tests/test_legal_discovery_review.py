import pytest

from weaponized.semiconductors.legal import issued_xml_text


def test_original_xml_requires_matching_issued_document_number():
    payload = b"<RULE><P>Effective <E>February 11</E>, 2025.</P><P>[FR Doc. 2025-02655 Filed 2-11-25; 4:15 pm]</P></RULE>"
    assert "Effective February 11 , 2025." in issued_xml_text(payload, "2025-02655")
    with pytest.raises(ValueError, match="identity mismatch"):
        issued_xml_text(payload, "2025-00711")
    with pytest.raises(ValueError, match="issued-document XML"):
        issued_xml_text(b"<html>Javascript challenge</html>", "2025-02655")
