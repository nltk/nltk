"""
Tests for ``nltk.xmlsec``, which blocks XML entity-expansion DoS (CWE-776).

Every case runs against both back ends: ``defusedxml`` when it is installed,
and the standard-library fallback used when it is not.  The two must agree,
because either may be the one protecting a given install.
"""

import importlib
import io
import sys
from xml.etree.ElementTree import ParseError

import pytest

from nltk import xmlsec


def _bomb(levels=5):
    """A "billion laughs" document; each level multiplies expansion by ten."""
    decls = "\n".join(
        f' <!ENTITY e{i} "{f"&e{i - 1};" * 10}">' for i in range(1, levels + 1)
    )
    return (
        '<?xml version="1.0"?>\n'
        f'<!DOCTYPE d [\n <!ENTITY e0 "AAAAAAAAAA">\n{decls}\n]>\n'
        f"<d><e>&e{levels};</e></d>"
    )


REJECTED = [
    pytest.param(_bomb(), id="billion-laughs"),
    pytest.param('<!DOCTYPE d [<!ENTITY a "x">]><d><e>&a;</e></d>', id="single-entity"),
    pytest.param(
        '<!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/passwd">]><d><e>hi</e></d>',
        id="external-entity-decl",
    ),
    # The subset's closing "]" must not be read out of a quoted literal, or a
    # declaration placed after it would slip through unscreened.
    pytest.param(
        '<!DOCTYPE d [<!ATTLIST d x CDATA "]"><!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="bracket-hidden-in-attlist",
    ),
    pytest.param(
        '<!DOCTYPE d [<!-- ] --><!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="bracket-hidden-in-comment",
    ),
    # Likewise the subset's opening "[" must not be read out of a SYSTEM literal.
    pytest.param(
        '<!DOCTYPE d SYSTEM "a[b.dtd" [<!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="bracket-in-system-literal",
    ),
    # Parser-differential payloads: a prolog comment or processing instruction
    # holding a decoy DOCTYPE, or a PI carrying a stray "]" inside the real
    # subset, must not distract the guard from the entity the real parse acts
    # on.  ElementTree expands every one of these.
    pytest.param(
        '<!-- <!DOCTYPE x [ ] > --><!DOCTYPE d [<!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="decoy-doctype-in-comment",
    ),
    pytest.param(
        '<?pi <!DOCTYPE x [ ] > ?><!DOCTYPE d [<!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="decoy-doctype-in-pi",
    ),
    pytest.param(
        '<!DOCTYPE d [ <?pi ]?> <!ENTITY a "BOOM"> ]><d><e>&a;</e></d>',
        id="stray-bracket-in-pi",
    ),
    pytest.param(
        '<!DOCTYPE d [<?x ]]]]?><!ENTITY a "BOOM">]><d><e>&a;</e></d>',
        id="stray-brackets-in-pi-data",
    ),
    # A parameter-entity declaration is an entity declaration too.
    pytest.param(
        '<!DOCTYPE d [<!ENTITY % pe "x">]><d><e>hi</e></d>',
        id="parameter-entity-decl",
    ),
]

ACCEPTED = [
    pytest.param("<d><e>Bob</e></d>", id="no-doctype"),
    # Real corpora name an external DTD; ElementTree never fetches it.
    pytest.param(
        '<!DOCTYPE d SYSTEM "apf.dtd"><d><e>Bob</e></d>', id="external-subset"
    ),
    pytest.param(
        '<!DOCTYPE d PUBLIC "-//X//DTD//EN" "x.dtd"><d><e>Bob</e></d>', id="public-id"
    ),
    pytest.param(
        "<!DOCTYPE d [<!ELEMENT d ANY>]><d><e>Bob</e></d>", id="subset-no-ents"
    ),
    # The five predefined entities need no declaration.
    pytest.param("<d><e>a &amp; b &lt; c</e></d>", id="builtin-escapes"),
    # "<!ENTITY" in content or CDATA is text, not a declaration.
    pytest.param("<d><e>the &lt;!ENTITY declaration</e></d>", id="entity-in-text"),
    pytest.param('<d><e><![CDATA[<!ENTITY a "x">]]></e></d>', id="entity-in-cdata"),
]


@pytest.fixture(params=["defusedxml", "fallback"])
def parser(request, monkeypatch):
    """``nltk.xmlsec`` with each back end forced."""
    if request.param == "defusedxml":
        pytest.importorskip("defusedxml")
        module = importlib.reload(xmlsec)
        assert module.HAVE_DEFUSEDXML
    else:
        # Hiding the module makes ``import defusedxml`` raise ImportError, so
        # reloading selects the standard-library path.
        monkeypatch.setitem(sys.modules, "defusedxml", None)
        module = importlib.reload(xmlsec)
        assert not module.HAVE_DEFUSEDXML
    yield module
    # Undo the patch *before* reloading: this fixture's teardown runs ahead of
    # monkeypatch's, so reloading first would re-select the fallback and leave
    # the module in that state for every later test.
    monkeypatch.undo()
    importlib.reload(xmlsec)


@pytest.mark.parametrize("xml", REJECTED)
def test_entity_declarations_are_rejected(parser, xml):
    with pytest.raises((ValueError, ParseError)):
        parser.fromstring(xml)
    with pytest.raises((ValueError, ParseError)):
        parser.parse(io.StringIO(xml))


@pytest.mark.parametrize("xml", ACCEPTED)
def test_benign_documents_still_parse(parser, xml):
    assert parser.fromstring(xml).find("e") is not None
    assert parser.parse(io.StringIO(xml)).getroot().find("e") is not None


def test_bomb_does_not_expand(parser):
    """The payload must be refused outright, not merely truncated."""
    with pytest.raises((ValueError, ParseError)):
        parser.fromstring(_bomb(levels=6))


def test_parse_accepts_a_filename(parser, tmp_path):
    path = tmp_path / "doc.xml"
    path.write_text("<d><e>Bob</e></d>", encoding="utf8")
    assert parser.parse(str(path)).getroot().find("e").text == "Bob"

    bomb = tmp_path / "bomb.xml"
    bomb.write_text(_bomb(), encoding="utf8")
    with pytest.raises((ValueError, ParseError)):
        parser.parse(str(bomb))


def test_utf16_prolog_is_screened(parser):
    """A non-ASCII encoding must not smuggle a declaration past the fallback."""
    with pytest.raises((ValueError, ParseError)):
        parser.parse(io.BytesIO(_bomb().encode("utf-16")))
