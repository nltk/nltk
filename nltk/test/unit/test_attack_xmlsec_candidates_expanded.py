# Natural Language Toolkit: expanded xmlsec candidate attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Net-new candidate matrix for ``nltk.xmlsec`` structured-format guards.

Companion to ``test_xmlsec.py``, ``test_xml_attack_matrix.py``,
``test_xml_entity_expansion_security.py`` and ``test_attack_xml_xss_expanded.py``.
It drives a broad set of plausible XML inputs, benign and hostile alike, through
the REAL guard, exercising BOTH entry points (:func:`nltk.xmlsec.fromstring` and
:func:`nltk.xmlsec.parse`) and BOTH back ends:

* ``defusedxml`` when it is installed, and
* the standard-library fallback whose pre-scan (:func:`nltk.xmlsec._reject_entities`)
  runs when ``defusedxml`` is absent (``HAVE_DEFUSEDXML`` False).

Guarantees asserted for every hostile input: it RAISES the entity guard
(``EntitiesForbidden`` / ``ValueError`` / ``ParseError``) OR, for a document that
merely NAMES an external subset or carries an inert XInclude, it parses with NO
outbound request (checked against a REAL loopback socket that must receive zero
connections). Benign documents keep parsing, and a markup payload smuggled in
CDATA / an attribute is neutralised at the serialization sink.

No mocking: the real parser runs on each input; ``file:///etc/passwd`` is bait
only (the raised exception is asserted, never file contents).
"""

import importlib
import io
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


def _billion_laughs(levels=6, seed="AAAAAAAAAA"):
    """Classic nested lolN billion-laughs; each level multiplies by ten."""
    decls = "".join(
        f'<!ENTITY e{i} "{f"&e{i - 1};" * 10}">' for i in range(1, levels + 1)
    )
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY e0 "{seed}">{decls}]>'
        f"<d><e>&e{levels};</e></d>"
    )


def _quadratic(entity_size=20000, refs=100):
    """Quadratic-blowup: one big entity referenced many times."""
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY a "{"A" * entity_size}">]>'
        f"<d>{'&a;' * refs}</d>"
    )


def _flat_entity(size=5000, refs=50):
    """A FLAT entity stock ElementTree expands (well under libexpat's cap);
    used as clean teeth that the guard still refuses."""
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE d [<!ENTITY a "{"A" * size}">]>'
        f"<d>{'&a;' * refs}</d>"
    )


# Every one of these DECLARES or REFERENCES an entity and must be refused.
ENTITY_REJECTED = {
    "billion-laughs": _billion_laughs(),
    "quadratic-blowup": _quadratic(),
    "flat-entity": _flat_entity(),
    "single-general-entity": '<!DOCTYPE d [<!ENTITY a "x">]><d><e>&a;</e></d>',
    "external-general-file": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><d><e>&xxe;</e></d>'
    ),
    "external-general-http": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest">]>'
        "<d><e>&xxe;</e></d>"
    ),
    "php-filter-wrapper": (
        '<?xml version="1.0"?>'
        "<!DOCTYPE d [<!ENTITY xxe SYSTEM "
        '"php://filter/convert.base64-encode/resource=/etc/passwd">]><d><e>&xxe;</e></d>'
    ),
    "parameter-entity": '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY % pe "x">]><d/>',
    "external-parameter-entity": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY % pe SYSTEM "file:///etc/passwd">%pe;]><d/>'
    ),
    "recursive-entity-chain": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY a "&b;"><!ENTITY b "&c;"><!ENTITY c "boom">]>'
        "<d><e>&a;</e></d>"
    ),
    "self-recursive-entity": (
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "&a;">]><d><e>&a;</e></d>'
    ),
    # Parser-differential decoys: a declaration hidden behind a bracket in a
    # comment / PI / literal that a naive string screener would skip, but expat
    # (and therefore the pre-scan) still acts on.
    "bracket-hidden-in-comment": (
        '<!DOCTYPE d [<!-- ] --><!ENTITY a "BOOM">]><d><e>&a;</e></d>'
    ),
    "bracket-in-system-literal": (
        '<!DOCTYPE d SYSTEM "a[b.dtd" [<!ENTITY a "BOOM">]><d><e>&a;</e></d>'
    ),
    "decoy-doctype-in-pi": (
        '<?pi <!DOCTYPE x [ ] > ?><!DOCTYPE d [<!ENTITY a "BOOM">]><d><e>&a;</e></d>'
    ),
}

# These merely NAME an external DTD; ElementTree never fetches it, so they PARSE
# but must issue no outbound request (checked against a live socket).
EXTERNAL_DTD_NAMED = {
    "doctype-system": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d SYSTEM "http://{host}:{port}/x.dtd"><d><e>Bob</e></d>'
    ),
    "doctype-public": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d PUBLIC "-//X//DTD Made Up//EN" '
        '"http://{host}:{port}/x.dtd"><d><e>Bob</e></d>'
    ),
}

# These REFERENCE an external resource and must be refused before any fetch.
EXTERNAL_REF_NO_FETCH = {
    "oob-parameter-entity": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY % rem SYSTEM "http://{host}:{port}/">%rem;]><d/>'
    ),
    "external-general-ref": (
        '<?xml version="1.0"?>'
        '<!DOCTYPE d [<!ENTITY x SYSTEM "http://{host}:{port}/">]><d><e>&x;</e></d>'
    ),
}

# Benign controls that must keep parsing on both entry points and back ends.
BENIGN_XML = {
    "no-doctype": "<d><e>Bob</e></d>",
    "nested-tree": "<corpus><doc id='1'><w pos='NN'>cat</w></doc></corpus>",
    "builtin-escapes": "<d><e>a &amp; b &lt; c &gt; d &quot; e &apos;</e></d>",
    "numeric-charref": "<d><e>&#65;&#x42;</e></d>",
    "external-subset-named": '<!DOCTYPE d SYSTEM "apf.dtd"><d><e>Bob</e></d>',
    "public-id-named": '<!DOCTYPE d PUBLIC "-//X//DTD//EN" "x.dtd"><d><e>Bob</e></d>',
    "subset-no-entities": "<!DOCTYPE d [<!ELEMENT d ANY>]><d><e>Bob</e></d>",
    "entity-word-in-text": "<d><e>the &lt;!ENTITY declaration</e></d>",
    "entity-word-in-cdata": '<d><e><![CDATA[<!ENTITY a "x">]]></e></d>',
}


# ===========================================================================
# Back-end fixture: force defusedxml present, then force the fallback
# ===========================================================================


@pytest.fixture(params=["defusedxml", "fallback"])
def backend(request, monkeypatch):
    """``nltk.xmlsec`` with each back end forced, restored on teardown."""
    if request.param == "defusedxml":
        pytest.importorskip("defusedxml")
        module = importlib.reload(xmlsec)
        assert module.HAVE_DEFUSEDXML
    else:
        # Hiding the module makes ``import defusedxml`` raise ImportError, so the
        # reload selects the standard-library pre-scan (fallback) path.
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


# ===========================================================================
# 1. Entity declarations / references are refused on BOTH entry points.
# ===========================================================================


@pytest.mark.parametrize(
    "payload", list(ENTITY_REJECTED.values()), ids=list(ENTITY_REJECTED)
)
def test_entity_payloads_refused_on_both_entry_points(backend, payload):
    _raises_guard(backend.fromstring, payload)
    _raises_guard(backend.parse, io.StringIO(payload))


def test_billion_laughs_refused_not_truncated(backend):
    """A deeper bomb is refused outright, not merely truncated."""
    _raises_guard(backend.fromstring, _billion_laughs(levels=8))
    _raises_guard(backend.parse, io.StringIO(_billion_laughs(levels=8)))


# ===========================================================================
# 2. Teeth: the payloads the guard refuses really do expand under stock
#    ElementTree, so a guard that stopped working would balloon memory.
# ===========================================================================


def test_teeth_flat_entity_expands_under_stock_elementtree():
    payload = _flat_entity(size=5000, refs=50)
    stock = StockET.fromstring(payload)
    # The flat entity expands directly into the root element's text.
    assert len(stock.text) == 5000 * 50  # stock expands it
    _raises_guard(xmlsec.fromstring, payload)  # xmlsec refuses the same bytes


def test_teeth_nested_bomb_expands_under_stock_elementtree():
    payload = _billion_laughs(levels=3, seed="AAAAAAAAAA")
    stock = StockET.fromstring(payload)
    assert len(stock.find("e").text) == 10 * 10**3
    _raises_guard(xmlsec.fromstring, payload)


# ===========================================================================
# 3. External DTD merely NAMED: parses, but no outbound request may go out.
# ===========================================================================


@pytest.mark.parametrize(
    "template", list(EXTERNAL_DTD_NAMED.values()), ids=list(EXTERNAL_DTD_NAMED)
)
def test_external_dtd_named_but_never_fetched(backend, template):
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
    listener = _Listener()
    payload = template.format(host=listener.host, port=listener.port)
    try:
        _raises_guard(backend.fromstring, payload)
    finally:
        listener.close()
    assert listener.connections == [], "refusal still leaked an outbound request"


# ===========================================================================
# 4. XInclude: ElementTree does not process xi:include during a plain parse, so
#    the include is INERT (no expansion) and issues no outbound request.
# ===========================================================================

XINCLUDE_NS = "http://www.w3.org/2001/XInclude"


def test_xinclude_is_inert_and_never_fetched(backend):
    listener = _Listener()
    payload = (
        '<?xml version="1.0"?>'
        f'<root xmlns:xi="{XINCLUDE_NS}">'
        f'<xi:include href="http://{listener.host}:{listener.port}/x" parse="text"/>'
        "<keep>Bob</keep></root>"
    )
    try:
        root = backend.fromstring(payload)
        # The include element is present but unexpanded (inert), and the sibling
        # content is intact; nothing was fetched.
        include = root.find(f"{{{XINCLUDE_NS}}}include")
        assert include is not None
        assert root.find("keep").text == "Bob"
    except (ValueError, ParseError):
        pass  # a refusal is also acceptable; either way nothing may be fetched
    finally:
        listener.close()
    assert listener.connections == [], "XInclude triggered an outbound fetch"


def test_xinclude_pointing_at_local_file_does_not_disclose(backend, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("NLTK-XINCLUDE-SENTINEL", encoding="utf-8")
    payload = (
        '<?xml version="1.0"?>'
        f'<root xmlns:xi="{XINCLUDE_NS}">'
        f'<xi:include href="{secret.as_uri()}" parse="text"/></root>'
    )
    root = backend.fromstring(payload)
    text = "".join(root.itertext())
    assert "NLTK-XINCLUDE-SENTINEL" not in text


# ===========================================================================
# 5. Encoding tricks: a non-ASCII encoding must not smuggle a declaration past
#    the pre-scan (the fallback feeds bytes to expat in their own type).
# ===========================================================================


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
def test_encoded_bomb_is_screened(backend, encoding):
    payload = _billion_laughs(levels=6).encode(encoding)
    _raises_guard(backend.parse, io.BytesIO(payload))


def test_utf8_bom_prefixed_bomb_is_screened(backend):
    payload = b"\xef\xbb\xbf" + _billion_laughs(levels=6).encode("utf-8")
    _raises_guard(backend.parse, io.BytesIO(payload))


# ===========================================================================
# 6. CDATA / attribute XSS payload: xmlsec parses it as inert TEXT (never a live
#    child element), and re-serialising the tree escapes it at the sink so no
#    live <script> tag can emerge.
# ===========================================================================


def test_cdata_script_is_inert_text_and_escaped_at_sink(backend):
    payload = (
        '<d attr="&quot;&gt;&lt;script&gt;"><![CDATA[<script>alert(1)</script>]]></d>'
    )
    element = backend.fromstring(payload)
    # CDATA content is inert text, not a parsed <script> child element.
    assert element.text == "<script>alert(1)</script>"
    assert list(element) == []
    # Re-serialising escapes the special characters: no live tag survives.
    serialized = StockET.tostring(element, encoding="unicode")
    assert "<script>" not in serialized
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in serialized


def test_attribute_markup_is_escaped_at_sink(backend):
    payload = '<d><w note="&lt;img src=x onerror=alert(1)&gt;">cat</w></d>'
    element = backend.fromstring(payload)
    note = element.find("w").attrib["note"]
    assert note == "<img src=x onerror=alert(1)>"  # inert attribute VALUE
    serialized = StockET.tostring(element, encoding="unicode")
    assert "<img" not in serialized  # re-escaped, no live tag at the sink


# ===========================================================================
# 7. BENIGN: ordinary XML keeps round-tripping on both entry points and back ends.
# ===========================================================================


@pytest.mark.parametrize("payload", list(BENIGN_XML.values()), ids=list(BENIGN_XML))
def test_benign_xml_still_parses_on_both_entry_points(backend, payload):
    assert (
        backend.fromstring(payload).find("e") is not None
        or backend.fromstring(payload).find("doc") is not None
    )
    assert backend.parse(io.StringIO(payload)).getroot() is not None


def test_benign_tree_has_the_right_shape(backend):
    root = backend.fromstring(
        "<corpus><doc id='1'><w pos='NN'>cat</w><w pos='NN'>dog</w></doc></corpus>"
    )
    words = root.findall("./doc/w")
    assert [w.text for w in words] == ["cat", "dog"]
    assert [w.attrib["pos"] for w in words] == ["NN", "NN"]


def test_parse_accepts_a_real_filename(backend, tmp_path):
    good = tmp_path / "ok.xml"
    good.write_text("<d><e>Bob</e></d>", encoding="utf-8")
    assert backend.parse(str(good)).getroot().find("e").text == "Bob"
    bomb = tmp_path / "bomb.xml"
    bomb.write_text(_billion_laughs(), encoding="utf-8")
    _raises_guard(backend.parse, str(bomb))


# ===========================================================================
# 8. Fallback pre-scan (HAVE_DEFUSEDXML False): _reject_entities is the guarantee
#    when defusedxml is absent. Confirm it refuses entities directly and lets
#    benign documents through, independent of which back end is installed.
# ===========================================================================


def _forced_fallback_module(monkeypatch):
    """Reload ``nltk.xmlsec`` with ``defusedxml`` hidden so HAVE_DEFUSEDXML is
    False and the module's own ``EntitiesForbidden`` / ``_reject_entities`` are
    the pre-scan actually used in that configuration."""
    monkeypatch.setitem(sys.modules, "defusedxml", None)
    module = importlib.reload(xmlsec)
    assert module.HAVE_DEFUSEDXML is False
    return module


def test_reject_entities_refuses_declarations_directly(monkeypatch):
    # In the fallback configuration _reject_entities is the guarantee; its own
    # standalone expat pass refuses any entity declaration or external reference.
    module = _forced_fallback_module(monkeypatch)
    try:
        for payload in (
            _billion_laughs(),
            '<!DOCTYPE d [<!ENTITY a "x">]><d><e>&a;</e></d>',
            '<!DOCTYPE d [<!ENTITY % pe "x">]><d/>',
            '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><d>&xxe;</d>',
        ):
            with pytest.raises(module.EntitiesForbidden):
                module._reject_entities(payload)
    finally:
        monkeypatch.undo()
        importlib.reload(xmlsec)


def test_reject_entities_allows_benign_documents(monkeypatch):
    # A benign document (no entity declaration) passes the pre-scan silently, and
    # a document merely naming an external subset is allowed (never fetched).
    module = _forced_fallback_module(monkeypatch)
    try:
        for payload in (
            "<d><e>Bob</e></d>",
            "<d><e>a &amp; b &lt; c</e></d>",
            '<!DOCTYPE d SYSTEM "apf.dtd"><d><e>Bob</e></d>',
            '<d><e><![CDATA[<!ENTITY a "x">]]></e></d>',
        ):
            assert module._reject_entities(payload) is None
    finally:
        monkeypatch.undo()
        importlib.reload(xmlsec)


def test_fallback_backend_refuses_entities_via_reject_entities(monkeypatch):
    # Force the fallback (HAVE_DEFUSEDXML False) explicitly and confirm the
    # entity refusal still holds through the public fromstring / parse API.
    module = _forced_fallback_module(monkeypatch)
    try:
        _raises_guard(module.fromstring, _billion_laughs())
        _raises_guard(module.parse, io.StringIO(_billion_laughs()))
        # Benign still parses on the fallback.
        assert module.fromstring("<d><e>Bob</e></d>").find("e").text == "Bob"
    finally:
        monkeypatch.undo()
        importlib.reload(xmlsec)
