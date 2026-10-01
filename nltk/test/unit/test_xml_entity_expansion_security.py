"""Regression tests for XML entity-expansion (Billion Laughs) in corpus readers (CWE-776).

NLTK's XML corpus readers parsed untrusted corpus XML with the stdlib
``xml.etree.ElementTree``, which performs entity expansion and is vulnerable to a
Billion-Laughs denial of service. They now parse via ``defusedxml`` (``safe_parse``
/ ``safe_fromstring``), which forbids the custom-entity definitions such an attack
relies on while leaving ordinary XML unaffected. This mirrors the fix applied to
the downloader's remote index in issue #3545 / PR #3544.
"""

import pytest
from defusedxml.common import EntitiesForbidden

from nltk.corpus.reader.xmldocs import XMLCorpusReader

# A Billion-Laughs payload: a tiny file whose nested entities would expand to a
# huge string with the stdlib parser.
_BOMB = (
    '<?xml version="1.0"?>\n'
    "<!DOCTYPE doc [\n"
    '  <!ENTITY a0 "AAAAAAAAAA">\n'
    '  <!ENTITY a1 "&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;">\n'
    '  <!ENTITY a2 "&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;">\n'
    '  <!ENTITY a3 "&a2;&a2;&a2;&a2;&a2;&a2;&a2;&a2;&a2;&a2;">\n'
    "]>\n"
    "<doc>&a3;</doc>"
)


def test_xmlcorpusreader_blocks_entity_bomb(tmp_path):
    """A malicious corpus file with a nested-entity DTD must be refused."""
    (tmp_path / "evil.xml").write_text(_BOMB)
    reader = XMLCorpusReader(str(tmp_path), ["evil.xml"])
    with pytest.raises(EntitiesForbidden):
        reader.xml("evil.xml")


def test_xmlcorpusreader_parses_normal_xml(tmp_path):
    """Ordinary XML, including the standard &amp;/&lt; entities, still parses."""
    (tmp_path / "ok.xml").write_text(
        '<doc><w pos="NN">cat</w> &amp; <w pos="NN">dog</w></doc>'
    )
    reader = XMLCorpusReader(str(tmp_path), ["ok.xml"])
    elt = reader.xml("ok.xml")
    assert elt.tag == "doc"
    assert reader.words("ok.xml") == ["cat", "dog"]
