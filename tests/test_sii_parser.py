import pytest
from academy.sii_parser import parse_sii, array_values
from academy.exceptions import ParseError


def test_values():
    objects = parse_sii('SiiNunit { unknown : a { entries: 2 entries[0]: b entries[1]: c text: "hi { : }" n: nil f: &abcd tuple: (1; 0, 0, 0) } }')
    assert array_values(objects["a"], "entries") == ["b", "c"]
    assert objects["a"].fields["n"] is None
    assert objects["a"].fields["f"] == "&abcd"
    assert objects["a"].fields["text"] == "hi { : }"


@pytest.mark.parametrize("text", ["SiiNunit {", "SiiNunit { x : a { k: } }", "SiiNunit { x : a { k: 1 k: 2 } }", "SiiNunit {} trailing"])
def test_bad_structure(text):
    with pytest.raises(ParseError):
        parse_sii(text)
