# Natural Language Toolkit: expanded tree-amplification attacks on nltk.xmlsec
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Documents that declare no entity yet build a tree hundreds or thousands of
times their size, driven through ``nltk.xmlsec`` and its real callers.

Four families, each measured before the chokepoint bounded them:

* DTD default attributes: ``<!ATTLIST e a1 CDATA "v" ... a200 CDATA "v">``
  over 2,000 ``<e/>``: 11 KB became 400,000 attributes and 13.5 MB of tree
  (1,230x); 63 KB became 12,000,000 attributes and 314 MB.  Long default
  values (59 KB to 108 MB), empty defaults (23 KB to 53 MB) and several
  ATTLIST declarations for one element (80 KB to 237 MB) are variants.
* Namespace expansion: a 20 KB ``xmlns`` URI over 5,000 distinct short names
  (59 KB) became 202 MB of ``{uri}local`` tag strings (3,423x).
* Depth: ``<a>`` nested 100,000 deep (700 KB) parses and then crashes the
  interpreter in ``copy.deepcopy``.
* Tokens: a single multi-megabyte tag, comment, PI or DOCTYPE literal.

Every attack is judged by what the tracemalloc peak reached, not only by the
exception: a refusal that first built the tree is no refusal.  Both back ends
(``defusedxml`` and the standard-library fallback) are driven, the payloads
are proven live under stock ElementTree, and benign neighbours (real corpora,
documents just under each ceiling, large text and CDATA runs, namespaced
documents with short URIs) pin that the ceilings do not over-block.  Control
characters are built with chr().
"""

import copy
import gc
import importlib
import io
import os
import shutil
import subprocess
import sys
import tracemalloc
from xml.etree import ElementTree as StockET
from xml.etree.ElementTree import ParseError

import pytest

import nltk
import nltk.data
from nltk import pathsec, xmlsec

MiB = 1024 * 1024

# Real-data shape from a scan of the whole NLTK data distribution (29,112 XML
# files, 1.7 GB); the ceilings must keep clear of every one of these.
REAL_MAX_ELEMENTS = 1_244_565  # brown_tei/Corpus.xml, 28 MB
REAL_MAX_ATTRIBUTES = 1_455_870  # alpino/alpino.xml, 22 MB
REAL_MAX_DEPTH = 26  # alpino/alpino.xml
REAL_MAX_TOKEN = 756  # framenet_v17/lu/lu7989.xml
REAL_MAX_EXPANSION = 1.02  # framenet_v17/lu/lu18812.xml


# ===========================================================================
# Payload builders
# ===========================================================================
def attlist(element, count, width=1, keyword=None):
    """``<!ATTLIST element a0 CDATA "v..." ...>`` with *count* defaults."""
    value = "v" * width
    default = f'#FIXED "{value}"' if keyword == "fixed" else f'"{value}"'
    return (
        f"<!ATTLIST {element} "
        + " ".join(f"a{i} CDATA {default}" for i in range(count))
        + ">"
    )


def defaults_doc(count=200, elements=2000, width=1, keyword=None, decls=1):
    subset = "".join(
        attlist("e", count, width, keyword) if d == 0 else attlist_more(d, count, width)
        for d in range(decls)
    )
    return (
        f'<?xml version="1.0"?><!DOCTYPE d [{subset}]><d>' + "<e/>" * elements + "</d>"
    )


def attlist_more(index, count, width):
    """A further ATTLIST for ``e`` whose names do not clash with the first."""
    value = "v" * width
    return (
        "<!ATTLIST e "
        + " ".join(f'b{index}_{i} CDATA "{value}"' for i in range(count))
        + ">"
    )


def namespace_doc(uri_len=20000, names=5000, attributes=False):
    uri = "u" * uri_len
    if attributes:
        body = "".join(f'<a p:b{i}=""/>' for i in range(names))
        return f'<r xmlns:p="{uri}">{body}</r>'
    body = "".join(f"<a{i}/>" for i in range(names))
    return f'<r xmlns="{uri}">{body}</r>'


def deep_doc(depth):
    return "<a>" * depth + "</a>" * depth


def token_doc(kind, size, char="x"):
    filler = char * size
    return {
        "attribute-value": f'<a b="{filler}"/>',
        "comment": f"<a><!--{filler}--></a>",
        "pi": f"<a><?pi {filler}?></a>",
        "doctype-literal": f'<!DOCTYPE a SYSTEM "{filler}"><a/>',
        "subset-comment": f"<!DOCTYPE a [<!--{filler}-->]><a/>",
        "element-name": f"<{filler}/>",
        "text": f"<a>{filler}</a>",
        "cdata": f"<a><![CDATA[{filler}]]></a>",
    }[kind]


AMPLIFIERS = {
    "dtd-defaults-200x2000": defaults_doc(),
    "dtd-defaults-1000x12000": defaults_doc(1000, 12000),
    "dtd-default-values-50x1000x2000": defaults_doc(50, 2000, width=1000),
    "dtd-empty-defaults-500x4000": defaults_doc(500, 4000, width=0),
    "dtd-several-attlists-300x200x3000": defaults_doc(1, 3000, width=200, decls=300),
    "dtd-fixed-defaults-100x3000": defaults_doc(100, 3000, keyword="fixed"),
    "namespace-element-names": namespace_doc(),
    "namespace-attribute-names": namespace_doc(2000, 20000, attributes=True),
    "namespace-2000x20000": namespace_doc(2000, 20000),
}
for _label, _doc in AMPLIFIERS.items():
    assert len(_doc) < 512 * 1024, (_label, len(_doc))


def count_attributes(root):
    return sum(len(element.attrib) for element in root.iter())


_snapshot = None


def peak_of(fn, *args):
    """Run under tracemalloc; return (outcome or exception, peak bytes).

    Garbage left by earlier tests is collected first, so a finaliser it would
    otherwise run inside the traced window (a writer flushing, a directory
    being reaped) is not charged to *fn*: the trace starts on a quiet heap and
    the peak is fn's own. Tracing must not already be running, or the peak
    would include whatever the earlier tracer saw. A peak past one MiB keeps a
    snapshot so ``where`` can say which lines allocated it.
    """
    global _snapshot
    gc.collect()
    assert not tracemalloc.is_tracing(), "an earlier test left tracemalloc running"
    tracemalloc.start()
    try:
        try:
            outcome = fn(*args)
        except Exception as exc:  # the outcome IS the refusal
            outcome = exc
        peak = tracemalloc.get_traced_memory()[1]
        _snapshot = tracemalloc.take_snapshot() if peak > MiB else None
        return outcome, peak
    finally:
        tracemalloc.stop()


def where(peak, note=""):
    """An assertion message naming the largest allocation sites of the last peak."""
    text = f"peak {peak} bytes"
    if note:
        text += f" ({note})"
    if _snapshot is not None:
        top = _snapshot.statistics("lineno")[:5]
        text += "; largest: " + "; ".join(
            f"{stat.size} B at {stat.traceback[0].filename}:{stat.traceback[0].lineno}"
            for stat in top
        )
    return text


def assert_refused_small(module, fn, doc, *args):
    """``fn`` must raise StructureForbidden with a peak that scales with the
    input (the screen may hold at most MAX_EXPANSION bytes per input byte
    plus one chunk), never with the tree the input describes."""
    outcome, peak = peak_of(fn, *args)
    assert isinstance(outcome, module.StructureForbidden), outcome
    assert isinstance(outcome, ValueError)
    budget = (module.MAX_EXPANSION + 4) * len(doc) + 2 * MiB
    assert peak <= budget, where(peak, f"for a {len(doc)} byte document")
    return outcome


# ===========================================================================
# Back-end fixture: defusedxml present, then the standard-library fallback
# ===========================================================================
@pytest.fixture(params=["defusedxml", "fallback"])
def backend(request, monkeypatch):
    """``nltk.xmlsec`` with each back end forced, restored on teardown."""
    if request.param == "defusedxml":
        pytest.importorskip("defusedxml")
        module = importlib.reload(xmlsec)
        assert module.HAVE_DEFUSEDXML
    else:
        monkeypatch.setitem(sys.modules, "defusedxml", None)
        module = importlib.reload(xmlsec)
        assert not module.HAVE_DEFUSEDXML
    yield module
    monkeypatch.undo()
    importlib.reload(xmlsec)


def write_in(root, name, document):
    path = os.path.join(str(root), name)
    # newline="" keeps the LF the documents are written with: Windows would
    # otherwise write CRLF, which the line-oriented readers do not expect
    mode = "wb" if isinstance(document, bytes) else "w"
    kwargs = {} if isinstance(document, bytes) else {"encoding": "utf-8", "newline": ""}
    with pathsec.open(path, mode, context="test", **kwargs) as handle:
        handle.write(document)
    return path


# ===========================================================================
# 1. Every amplifier is refused small on every entry point and back end
# ===========================================================================
class TestAmplifiers:
    @pytest.mark.parametrize("label", list(AMPLIFIERS))
    def test_refused_on_fromstring_and_parse(self, backend, label):
        doc = AMPLIFIERS[label]
        assert_refused_small(backend, backend.fromstring, doc, doc)
        assert_refused_small(backend, backend.parse, doc, io.StringIO(doc))
        raw = doc.encode("utf-8")
        assert_refused_small(backend, backend.parse, raw, io.BytesIO(raw))

    @pytest.mark.parametrize(
        "label", ["dtd-defaults-200x2000", "namespace-element-names"]
    )
    def test_refused_from_a_filename(self, backend, pathsec_sandbox, label):
        root, outside = pathsec_sandbox
        doc = AMPLIFIERS[label]
        path = write_in(root, "doc.xml", doc)
        assert_refused_small(backend, backend.parse, doc, path)

    @pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
    def test_an_encoded_default_bomb_is_screened(self, backend, encoding):
        raw = defaults_doc().encode(encoding)
        assert_refused_small(backend, backend.parse, raw, io.BytesIO(raw))

    def test_a_bom_prefixed_default_bomb_is_screened(self, backend):
        raw = b"\xef\xbb\xbf" + defaults_doc().encode("utf-8")
        assert_refused_small(backend, backend.parse, raw, io.BytesIO(raw))

    def test_the_refusal_comes_before_a_malformed_tail_is_reached(self, backend):
        # The screen refuses the expansion it has counted; it never defers a
        # document that is both amplifying and, later, malformed.
        doc = defaults_doc()[: -len("</d>")] + "<oops"
        assert_refused_small(backend, backend.fromstring, doc, doc)

    def test_a_merely_malformed_document_is_deferred_to_the_parser(self, backend):
        outcome, peak = peak_of(backend.fromstring, "<a><b></a>")
        assert isinstance(outcome, ParseError), outcome
        assert peak < MiB, where(peak)


# ===========================================================================
# 2. Teeth: the same payloads balloon under stock ElementTree / defusedxml
# ===========================================================================
class TestTeeth:
    def test_dtd_defaults_expand_under_stock_elementtree(self):
        doc = AMPLIFIERS["dtd-defaults-200x2000"]
        root, peak = peak_of(StockET.fromstring, doc)
        assert count_attributes(root) == 200 * 2000
        assert peak > 10 * MiB, f"peak {peak} for {len(doc)} bytes"
        assert peak > 500 * len(doc)  # the amplification the ceiling refuses

    def test_dtd_defaults_expand_under_stock_defusedxml(self):
        defused = pytest.importorskip("defusedxml.ElementTree")
        doc = AMPLIFIERS["dtd-defaults-200x2000"]
        root, peak = peak_of(defused.fromstring, doc)
        assert count_attributes(root) == 200 * 2000
        assert peak > 500 * len(doc)

    def test_a_long_namespace_expands_under_stock_elementtree(self):
        doc = namespace_doc(5000, 4000)  # 4,000 tags of 5 KB each: 20 MB
        root, peak = peak_of(StockET.fromstring, doc)
        assert sum(len(element.tag) for element in root.iter()) > 20_000_000
        assert peak > 200 * len(doc)

    def test_a_deep_tree_cannot_be_serialised_or_copied_safely(self):
        root = StockET.fromstring(deep_doc(5000))
        with pytest.raises(RecursionError):
            StockET.tostring(root)
        # deepcopy recurses in C: past the stack it kills the interpreter, so
        # it runs in a child, which must not come back reporting success.
        depth = 400_000
        code = (
            "import copy\nfrom xml.etree import ElementTree as ET\n"
            f"root = ET.fromstring('<a>' * {depth} + '</a>' * {depth})\n"
            "copy.deepcopy(root)\nprint('DEEPCOPY-OK')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=300
        )
        assert not (proc.returncode == 0 and "DEEPCOPY-OK" in proc.stdout), (
            "stock ElementTree deep-copied a 400,000-deep tree: the depth "
            "ceiling has nothing to protect on this platform"
        )


# ===========================================================================
# 3. Depth and single-token ceilings
# ===========================================================================
class TestDepthAndTokens:
    def test_depth_at_the_ceiling_parses_and_one_past_it_is_refused(self, backend):
        root = backend.fromstring(deep_doc(backend.MAX_DEPTH))
        assert root.tag == "a"
        with pytest.raises(backend.StructureForbidden, match="nesting depth"):
            backend.fromstring(deep_doc(backend.MAX_DEPTH + 1))

    def test_a_very_deep_document_is_refused_without_crashing(self, backend):
        doc = deep_doc(100_000)
        outcome, peak = peak_of(backend.fromstring, doc)
        assert isinstance(outcome, backend.StructureForbidden), outcome
        # depth is judged on the built tree, so the peak is the tree (linear
        # in the input, about 40x), never the crash that would follow
        assert peak < 64 * MiB, where(peak)
        tree_outcome, _ = peak_of(backend.parse, io.StringIO(doc))
        assert isinstance(tree_outcome, backend.StructureForbidden)

    @pytest.mark.parametrize(
        "kind",
        [
            "attribute-value",
            "comment",
            "pi",
            "doctype-literal",
            "subset-comment",
            "element-name",
        ],
    )
    def test_a_token_a_chunk_past_the_ceiling_is_refused(self, backend, kind):
        doc = token_doc(kind, backend.MAX_TOKEN_BYTES + 2 * 64 * 1024)
        outcome, peak = peak_of(backend.fromstring, doc)
        assert isinstance(outcome, backend.StructureForbidden), outcome
        assert "markup token" in str(outcome)
        assert peak < 8 * MiB, where(peak)
        outcome, _ = peak_of(backend.parse, io.BytesIO(doc.encode()))
        assert isinstance(outcome, backend.StructureForbidden), outcome

    @pytest.mark.parametrize(
        "kind",
        [
            "attribute-value",
            "comment",
            "pi",
            "doctype-literal",
            "subset-comment",
            "element-name",
        ],
    )
    @pytest.mark.parametrize("over", [1, 10, 1000, 64 * 1024 - 1])
    def test_a_token_one_byte_past_the_ceiling_is_refused(self, backend, kind, over):
        # The feed is cut where a pending token would pass the ceiling, so the
        # refusal is exact on every expat: before that cut, an expat without
        # reparse deferral (before 2.6, e.g. Python 3.9's 2.2.8 and some 3.10
        # builds) completed a token up to one 64 KiB chunk longer unseen.
        doc = token_doc(kind, backend.MAX_TOKEN_BYTES + over)
        with pytest.raises(backend.StructureForbidden, match="markup token"):
            backend.fromstring(doc)
        with pytest.raises(backend.StructureForbidden, match="markup token"):
            backend.parse(io.BytesIO(doc.encode()))

    @pytest.mark.parametrize("kind", ["attribute-value", "comment", "pi"])
    @pytest.mark.parametrize("width", [2, 3, 4])
    @pytest.mark.parametrize("over", [1, 1000, 64 * 1024 - 1])
    def test_a_multibyte_token_past_the_ceiling_is_refused(
        self, backend, kind, width, over
    ):
        # The ceiling counts bytes while a str is sliced in characters: the
        # text feed must be cut at the byte, or an expat without reparse
        # deferral completes a token up to a chunk longer, exactly as before
        char = {2: chr(0xE9), 3: chr(0x4E2D), 4: chr(0x1F600)}[width]
        doc = token_doc(kind, -(-(backend.MAX_TOKEN_BYTES + over) // width), char)
        with pytest.raises(backend.StructureForbidden, match="markup token"):
            backend.fromstring(doc)
        with pytest.raises(backend.StructureForbidden, match="markup token"):
            backend.parse(io.BytesIO(doc.encode()))

    @pytest.mark.parametrize("kind", ["attribute-value", "comment", "pi"])
    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_a_multibyte_token_under_the_ceiling_parses(self, backend, kind, width):
        char = {2: chr(0xE9), 3: chr(0x4E2D), 4: chr(0x1F600)}[width]
        doc = token_doc(kind, (backend.MAX_TOKEN_BYTES - 4096) // width, char)
        assert backend.fromstring(doc) is not None
        assert backend.parse(io.BytesIO(doc.encode())).getroot() is not None

    @pytest.mark.parametrize("kind", ["attribute-value", "comment", "element-name"])
    def test_a_token_under_the_ceiling_parses(self, backend, kind):
        doc = token_doc(kind, backend.MAX_TOKEN_BYTES - 4096)
        assert backend.fromstring(doc) is not None

    @pytest.mark.parametrize("kind", ["text", "cdata"])
    def test_text_and_cdata_runs_are_not_tokens(self, backend, kind):
        doc = token_doc(kind, 4 * MiB)
        root = backend.fromstring(doc)
        assert len(root.text) == 4 * MiB

    def test_a_large_document_of_small_tokens_is_not_over_blocked(self, backend):
        doc = (
            "<a><!--"
            + "c" * 900_000
            + "-->"
            + "t" * (8 * MiB)
            + "".join(f'<b v="{"x" * 60_000}"/>' for _ in range(50))
            + "<c>x</c>" * 200_000
            + "</a>"
        )
        root = backend.fromstring(doc)
        assert len(root) == 200_050


# ===========================================================================
# 4. Arming rules, ratio boundaries and the ceilings themselves
# ===========================================================================
class TestCeilings:
    def test_the_ceilings_clear_every_real_nltk_data_file_with_headroom(self):
        assert xmlsec.MAX_ELEMENTS == 20_000_000 >= 16 * REAL_MAX_ELEMENTS
        assert xmlsec.MAX_ATTRIBUTES == 20_000_000 >= 13 * REAL_MAX_ATTRIBUTES
        assert xmlsec.MAX_DEPTH == 1_000 >= 38 * REAL_MAX_DEPTH
        assert xmlsec.MAX_TOKEN_BYTES == MiB >= 1000 * REAL_MAX_TOKEN
        assert xmlsec.MAX_EXPANSION == 16 >= 15 * REAL_MAX_EXPANSION
        assert xmlsec._LONG_NAMESPACE == 64
        for name in (
            "MAX_ELEMENTS",
            "MAX_ATTRIBUTES",
            "MAX_DEPTH",
            "MAX_TOKEN_BYTES",
            "MAX_EXPANSION",
        ):
            assert name in xmlsec.__all__

    def test_implied_and_required_attlists_do_not_arm_or_refuse(self, backend):
        doc = (
            "<!DOCTYPE d [<!ATTLIST e a CDATA #IMPLIED b CDATA #REQUIRED>]><d>"
            + '<e b="1"/>' * 3000
            + "</d>"
        )
        root, peak = peak_of(backend.fromstring, doc)
        assert len(root) == 3000 and peak < 4 * MiB

    def test_a_few_defaults_per_element_stay_under_the_ratio(self, backend):
        # four one-byte defaults cost 36 per four-byte element: ratio 9
        doc = defaults_doc(4, 3000)
        root = backend.fromstring(doc)
        assert count_attributes(root) == 4 * 3000

    def test_nine_defaults_per_element_cross_the_ratio(self, backend):
        # nine cost 81 per four-byte element: ratio 20
        doc = defaults_doc(9, 3000)
        assert_refused_small(backend, backend.fromstring, doc, doc)

    def test_short_namespaces_over_many_distinct_names_are_allowed(self, backend):
        doc = namespace_doc(64, 20000)
        root = backend.fromstring(doc)
        assert len(root) == 20000 and root[0].tag == "{" + "u" * 64 + "}a0"

    def test_a_long_namespace_over_one_repeated_name_is_allowed(self, backend):
        doc = f'<r xmlns="{"u" * 2000}">' + "<a/>" * 20000 + "</r>"
        root = backend.fromstring(doc)
        assert len(root) == 20000

    def test_real_namespace_uris_are_all_under_the_arming_length(self):
        for uri in (
            "http://www.tei-c.org/ns/1.0",
            "http://framenet.icsi.berkeley.edu",
            "http://www.w3.org/2001/XMLSchema-instance",
            "http://www.w3.org/XML/1998/namespace",
            "http://www.talkbank.org/ns/talkbank",
            "http://www.w3.org/2001/XInclude",
        ):
            assert len(uri) <= xmlsec._LONG_NAMESPACE, uri

    def test_element_ceiling_is_counted_while_armed(self, backend, monkeypatch):
        monkeypatch.setattr(backend, "MAX_ELEMENTS", 1000)
        doc = defaults_doc(1, 1001)  # armed by the default; 1,002 elements
        with pytest.raises(backend.StructureForbidden, match="element count"):
            backend.fromstring(doc)
        assert len(backend.fromstring(defaults_doc(1, 998))) == 998

    def test_attribute_ceiling_counts_defaults_and_explicit_alike(
        self, backend, monkeypatch
    ):
        monkeypatch.setattr(backend, "MAX_ATTRIBUTES", 1000)
        with pytest.raises(backend.StructureForbidden, match="attribute count"):
            backend.fromstring(defaults_doc(2, 501))
        # explicit attributes in an input big enough to reach the ceiling
        # arm the counter too: 4 * 1000 bytes is the arming threshold
        doc = "<d>" + '<e a="1"/>' * 1001 + "</d>"
        assert len(doc) > 4 * 1000
        with pytest.raises(backend.StructureForbidden, match="attribute count"):
            backend.fromstring(doc)
        assert len(backend.fromstring("<d>" + '<e a="1"/>' * 999 + "</d>")) == 999

    def test_the_tree_walk_refuses_a_built_tree_over_the_element_ceiling(
        self, monkeypatch
    ):
        monkeypatch.setattr(xmlsec, "MAX_ELEMENTS", 1000)
        root = StockET.Element("d")
        root.extend(StockET.Element("e") for _ in range(1000))
        with pytest.raises(xmlsec.StructureForbidden, match="element count"):
            xmlsec._check_tree(root)
        del root[-1]
        assert xmlsec._check_tree(root) is None

    def test_raising_a_ceiling_admits_a_trusted_document(self, backend, monkeypatch):
        doc = defaults_doc(9, 3000)
        with pytest.raises(backend.StructureForbidden):
            backend.fromstring(doc)
        monkeypatch.setattr(backend, "MAX_EXPANSION", 64)
        assert count_attributes(backend.fromstring(doc)) == 9 * 3000


# ===========================================================================
# 5. Entities keep their refusal and their exception classes
# ===========================================================================
class TestEntitiesStillRefused:
    @pytest.mark.parametrize(
        "doc, kind",
        [
            ('<!DOCTYPE d [<!ENTITY a "x">]><d>&a;</d>', "Entities"),
            ('<!DOCTYPE d [<!ENTITY % p "x">]><d/>', "Entities"),
            (
                '<!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/passwd">]><d>&x;</d>',
                "Entities",
            ),
            (
                '<!DOCTYPE d [<!ENTITY % p SYSTEM "file:///etc/passwd">%p;]><d/>',
                "Entities",
            ),
        ],
    )
    def test_entity_payloads_raise_the_entity_class(self, backend, doc, kind):
        with pytest.raises(ValueError) as excinfo:
            backend.fromstring(doc)
        assert (
            kind in type(excinfo.value).__name__
            or "Forbidden" in type(excinfo.value).__name__
        )
        with pytest.raises(ValueError):
            backend.parse(io.StringIO(doc))

    def test_an_entity_ahead_of_a_default_bomb_is_the_refusal_reported(self, backend):
        doc = (
            '<!DOCTYPE d [<!ENTITY a "x">'
            + attlist("e", 200)
            + "]><d>"
            + "<e/>" * 2000
            + "</d>"
        )
        with pytest.raises(backend.EntitiesForbidden):
            backend.fromstring(doc)

    def test_a_default_bomb_ahead_of_an_entity_is_still_refused(self, backend):
        doc = (
            "<!DOCTYPE d ["
            + attlist("e", 200)
            + '<!ENTITY a "x">]><d>'
            + "<e/>" * 2000
            + "</d>"
        )
        with pytest.raises(ValueError):
            backend.fromstring(doc)

    def test_reject_entities_still_answers_for_the_fallback(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "defusedxml", None)
        module = importlib.reload(xmlsec)
        try:
            assert module._reject_entities("<d><e>Bob</e></d>") is None
            with pytest.raises(module.EntitiesForbidden):
                module._reject_entities('<!DOCTYPE d [<!ENTITY a "x">]><d>&a;</d>')
            with pytest.raises(module.StructureForbidden):
                module._reject_entities(AMPLIFIERS["dtd-defaults-200x2000"])
        finally:
            monkeypatch.undo()
            importlib.reload(xmlsec)


# ===========================================================================
# 6. Encoding parity between the screen and the parser
# ===========================================================================
class TestEncodingParity:
    def test_an_unsupported_multibyte_encoding_fails_the_same_way(self, backend):
        doc = b'<?xml version="1.0" encoding="gb2312"?><a/>'
        with pytest.raises(ValueError) as ours:
            backend.fromstring(doc)
        with pytest.raises(ValueError) as stock:
            StockET.fromstring(doc)
        assert str(ours.value) == str(stock.value)

    def test_a_lone_surrogate_fails_the_same_way(self, backend):
        doc = "<a>" + chr(0xDC80) + "</a>"
        with pytest.raises(UnicodeEncodeError):
            backend.fromstring(doc)
        with pytest.raises(UnicodeEncodeError):
            StockET.fromstring(doc)

    def test_a_str_with_a_utf16_declaration_is_read_as_the_parser_reads_it(
        self, backend
    ):
        # ElementTree forces UTF-8 on a str, so the screen must too: fed as
        # bytes the declaration would apply and the count would be lost
        doc = '<?xml version="1.0" encoding="utf-16"?>' + defaults_doc()[21:]
        assert_refused_small(backend, backend.fromstring, doc, doc)

    def test_multibyte_text_and_names_across_chunk_boundaries(self, backend):
        doc = (
            "<a>"
            + chr(0x4E2D) * 500_000
            + "".join(f"<{chr(0x4E2D)}{i}/>" for i in range(20000))
            + "</a>"
        )
        assert len(backend.fromstring(doc)) == 20000
        assert len(backend.parse(io.BytesIO(doc.encode())).getroot()) == 20000


# ===========================================================================
# 7. Real callers, with corpus-shaped documents
# ===========================================================================
def bcp47_files(count=300, elements=2000):
    """A CLDR subdivisions file with *count* defaults per subdivision, and a
    minimal IANA registry, the two files BCP47CorpusReader reads."""
    subdivisions = "".join(
        f'<subdivision type="t{i}">name {i}</subdivision>' for i in range(elements)
    )
    attack = (
        '<?xml version="1.0" encoding="utf-8"?><!DOCTYPE ldml ['
        + attlist("subdivision", count, 8)
        + "]><ldml><localeDisplayNames><subdivisions>"
        + subdivisions
        + "</subdivisions></localeDisplayNames></ldml>"
    )
    benign = (
        '<?xml version="1.0" encoding="utf-8"?><ldml><localeDisplayNames>'
        "<subdivisions>" + subdivisions + "</subdivisions></localeDisplayNames></ldml>"
    )
    registry = (
        "File-Date: 2024-01-01\n%%\nType: language\nSubtag: en\n"
        "Description: English\nAdded: 2005-10-16\n%%\nType: region\nSubtag: GB\n"
        "Description: United Kingdom\nAdded: 2005-10-16\n"
    )
    return attack, benign, registry


def ace_files(count=300, entities=100, mentions=20):
    mention = (
        '<entity_mention TYPE="NAME"><head><charseq><start>0</start>'
        "<end>2</end></charseq></head></entity_mention>"
    )
    document = "".join(
        "<entity><entity_type>PER</entity_type>" + mention * mentions + "</entity>"
        for _ in range(entities)
    )
    attack = (
        '<?xml version="1.0"?><!DOCTYPE source_file ['
        + attlist("entity_mention", count, 8)
        + "]><source_file><document>"
        + document
        + "</document></source_file>"
    )
    benign = (
        '<?xml version="1.0"?><source_file><document>'
        + document
        + "</document></source_file>"
    )
    text = "<DOC><TEXT>Bob went home to see Ann.</TEXT></DOC>"
    return attack, benign, text


def find_real_punkt():
    """The real punkt_tab model, as ``("dir", path)`` or ``("zip", path)``, or
    None: named_entity tokenises with word_tokenize after it has parsed the
    annotation file, and nltk.data reads the model from either form."""
    for base in nltk.data.path + [os.path.expanduser("~/nltk_data")]:
        unpacked = os.path.join(base, "tokenizers", "punkt_tab")
        if os.path.isdir(os.path.join(unpacked, "english")):
            return "dir", unpacked
        packed = os.path.join(base, "tokenizers", "punkt_tab.zip")
        if os.path.isfile(packed):
            return "zip", packed
    return None


class TestCallers:
    def test_bcp47_reader_refuses_a_default_bomb_and_reads_a_real_shape(
        self, pathsec_sandbox
    ):
        from nltk.corpus.reader.bcp47 import BCP47CorpusReader

        root, outside = pathsec_sandbox
        attack, benign, registry = bcp47_files()
        base = root / "corpora" / "bcp47"
        (base / "cldr").mkdir(parents=True)
        (base / "iana").mkdir()
        write_in(base / "iana", "language-subtag-registry.txt", registry)
        write_in(base / "cldr", "common-subdivisions-en.xml", attack)
        outcome, peak = peak_of(BCP47CorpusReader, str(base), r"(cldr|iana)/*")
        assert isinstance(outcome, xmlsec.StructureForbidden), outcome
        assert peak < 4 * MiB, where(peak, f"for an {len(attack)} byte file")
        write_in(base / "cldr", "common-subdivisions-en.xml", benign)
        reader = BCP47CorpusReader(str(base), r"(cldr|iana)/*")
        assert len(reader.subdiv) == 2000 and reader.subdiv["t7"] == "name 7"
        assert reader.langcode["English"] == "en"

    def test_named_entity_ace_loader_refuses_a_default_bomb(self, pathsec_sandbox):
        from nltk.chunk.named_entity import load_ace_file

        root, outside = pathsec_sandbox
        attack, benign, text = ace_files()
        base = root / "corpora" / "ace_data"
        base.mkdir(parents=True)
        write_in(base, "doc.sgm", text)
        write_in(base, "doc.sgm.tmx.rdc.xml", attack)
        outcome, peak = peak_of(
            lambda: list(load_ace_file(str(base / "doc.sgm"), "binary"))
        )
        assert isinstance(outcome, xmlsec.StructureForbidden), outcome
        assert peak < 8 * MiB, where(peak, f"for a {len(attack)} byte file")

    def test_named_entity_ace_loader_still_reads_a_benign_file(self, pathsec_sandbox):
        from nltk.chunk.named_entity import load_ace_file

        punkt = find_real_punkt()
        if punkt is None:
            pytest.skip("the real punkt_tab model is not installed")
        root, outside = pathsec_sandbox
        kind, source = punkt
        (root / "tokenizers").mkdir()
        if kind == "dir":
            shutil.copytree(source, str(root / "tokenizers" / "punkt_tab"))
        else:
            shutil.copyfile(source, str(root / "tokenizers" / "punkt_tab.zip"))
        attack, benign, text = ace_files()
        base = root / "corpora" / "ace_data"
        base.mkdir(parents=True)
        write_in(base, "doc.sgm", text)
        write_in(base, "doc.sgm.tmx.rdc.xml", benign)
        sentences = list(load_ace_file(str(base / "doc.sgm"), "binary"))
        assert len(sentences) == 1 and sentences[0].label() == "S"
        assert any(
            getattr(node, "label", None) and node.label() == "NE"
            for node in sentences[0]
        )

    def test_element_wrapper_refuses_a_default_bomb_and_wraps_a_benign_string(self):
        from nltk.internals import ElementWrapper

        doc = AMPLIFIERS["dtd-defaults-200x2000"]
        outcome, peak = peak_of(ElementWrapper, doc)
        assert isinstance(outcome, xmlsec.StructureForbidden), outcome
        assert peak < 2 * MiB, where(peak)
        outcome, peak = peak_of(ElementWrapper, AMPLIFIERS["namespace-element-names"])
        assert isinstance(outcome, xmlsec.StructureForbidden), outcome
        assert peak < 4 * MiB, where(peak)
        wrapped = ElementWrapper("<test><e a='1'>x</e></test>")
        assert wrapped.find("e").get("a") == "1" and wrapped.unwrap().tag == "test"
        assert str(wrapped).endswith('<test><e a="1">x</e></test>')

    def test_package_fromxml_refuses_a_default_bomb_file(self, pathsec_sandbox):
        from nltk.downloader import Package

        root, outside = pathsec_sandbox
        doc = (
            '<?xml version="1.0"?><!DOCTYPE package ['
            + attlist("p", 200)
            + ']><package id="x" url="http://127.0.0.1/x.zip" size="1" '
            'unzipped_size="1" subdir="corpora">' + "<p/>" * 2000 + "</package>"
        )
        path = write_in(root, "package.xml", doc)
        outcome, peak = peak_of(Package.fromxml, path)
        assert isinstance(outcome, xmlsec.StructureForbidden), outcome
        assert peak < 2 * MiB, where(peak)


# ===========================================================================
# 8. Real corpora still parse through the readers that hold them
# ===========================================================================
def corpus_or_skip(name):
    reader = getattr(nltk.corpus, name)
    try:
        reader.fileids()
    except LookupError:
        pytest.skip(f"the {name} corpus is not installed")
    return reader


class TestRealData:
    def test_verbnet(self):
        verbnet = corpus_or_skip("verbnet")
        vnclass = verbnet.vnclass("pelt-17.2")
        assert [m.get("name") for m in vnclass.findall("MEMBERS/MEMBER")][:2] == [
            "bombard",
            "buffet",
        ]
        assert len(verbnet.classids()) > 200
        give = verbnet.classids("give")
        assert give and all(c.startswith("give-13.1") for c in give)
        assert "give" in verbnet.lemmas(give[0])

    def test_rte(self):
        rte = corpus_or_skip("rte")
        pairs = rte.pairs("rte3_dev.xml")
        assert len(pairs) == 800 and pairs[0].text

    def test_shakespeare(self):
        shakespeare = corpus_or_skip("shakespeare")
        play = shakespeare.xml("dream.xml")
        assert play.find("TITLE").text.startswith("A Midsummer")
        assert len(play.findall(".//SPEECH")) > 100

    def test_nps_chat(self):
        nps_chat = corpus_or_skip("nps_chat")
        posts = nps_chat.posts(nps_chat.fileids()[0])
        assert len(posts) > 100 and posts[0]

    def test_bcp47(self):
        bcp47 = corpus_or_skip("bcp47")
        assert bcp47.name("oc-gascon-u-sd-fr64") == (
            "Occitan (post 1500): Gascon: Pyr"
            + chr(0xE9)
            + "n"
            + chr(0xE9)
            + "es-Atlantiques"
        )

    def test_framenet(self):
        framenet = corpus_or_skip("framenet")
        frame = framenet.frame("Apply_heat")
        assert frame.name == "Apply_heat" and len(frame.lexUnit) > 10
        lu = framenet.lu(256)
        assert lu.name and lu.frame.name

    def test_semcor(self):
        semcor = corpus_or_skip("semcor")
        sents = semcor.tagged_sents(semcor.fileids()[0])
        assert len(sents[0]) > 3

    def test_propbank_and_nombank(self):
        propbank = corpus_or_skip("propbank")
        assert propbank.roleset("give.01").get("id") == "give.01"
        nombank = corpus_or_skip("nombank")
        assert nombank.roleset("actor.01").get("id") == "actor.01"

    def test_senseval(self):
        senseval = corpus_or_skip("senseval")
        instance = senseval.instances("hard.pos")[0]
        assert instance.word == "hard-a" and instance.senses

    def test_multext_east(self):
        multext = corpus_or_skip("multext_east")
        words = multext.words("oana-en.xml")
        assert len(words[:20]) == 20

    def test_the_real_downloader_index_shape_passes_every_ceiling(self):
        # 551 elements, 1,852 attributes, no namespace: the live index shape
        from nltk.downloader import Package

        body = (
            '<?xml version="1.0"?><nltk_data><packages>'
            + "".join(
                f'<package id="p{i}" name="Package {i}" subdir="corpora" '
                f'url="https://example.invalid/p{i}.zip" size="{i}" '
                f'unzipped_size="{i}" checksum="{"0" * 32}" '
                f'author="A" license="L" webpage="https://example.invalid/"/>'
                for i in range(122)
            )
            + "</packages><collections>"
            + "".join(
                f'<collection id="c{i}" name="C{i}">'
                + "".join(f'<item ref="p{j}"/>' for j in range(i, 122, 7))
                + "</collection>"
                for i in range(7)
            )
            + "</collections></nltk_data>"
        )
        root = xmlsec.fromstring(body)
        packages = [Package.fromxml(p) for p in root.findall("packages/package")]
        assert len(packages) == 122
