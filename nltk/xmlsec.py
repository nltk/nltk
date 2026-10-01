# Natural Language Toolkit: Safer XML parsing.
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""XML parsing helpers that refuse entity declarations and bound the tree.

``xml.etree.ElementTree`` honours ``<!ENTITY>`` declarations in a document's
internal DTD subset, so a small file can expand to an arbitrarily large string
in memory: the "billion laughs" / entity-expansion DoS (CWE-776).  A 330-byte
document expands to a megabyte with five levels of nesting, and each further
level multiplies by ten.

libexpat 2.6.0 (2024) added an input-amplification cap, but it only engages
above an activation threshold (~8 MiB of output by default) and belongs to
whatever libexpat the running interpreter links, not to NLTK.  Builds against
an older system libexpat have no cap at all.  These helpers make the guarantee
NLTK's own.

:func:`parse` and :func:`fromstring` use ``defusedxml`` when it is installed and
fall back to an equivalent standard-library implementation when it is not, so
NLTK is protected either way and ``defusedxml`` stays an optional dependency.

External entities are *not* the concern here (``ElementTree`` does not resolve
them; it reports ``undefined entity``) but the fallback rejects them too, for
parity with ``defusedxml``'s ``forbid_external`` default.

What is rejected
----------------
Any document that *declares* an entity (general or parameter) or references an
external one.  A DOCTYPE that merely names an external DTD (``<!DOCTYPE corpus
SYSTEM "apf.dtd">``) is *allowed*, because real corpora use them and
ElementTree never fetches the external subset anyway.  The five predefined XML
entities (``&amp;`` ``&lt;`` ``&gt;`` ``&quot;`` ``&apos;``) and numeric
character references need no declaration and keep working.  Both back ends agree
on this policy.

What is bounded
---------------
Entities are not the only way a few kilobytes become a huge tree.  Neither back
end limits these, so every document is screened with a streaming expat pass
that builds nothing and refuses (:class:`StructureForbidden`) before a tree is
built:

* **DTD default attributes.**  ``<!ATTLIST e a1 CDATA "v" ... a200 CDATA "v">``
  declares no entity, yet every ``<e/>`` (four bytes) silently gains 200
  attributes.  An 11 KB document built 400,000 attributes and 13 MB of tree;
  63 KB built 12,000,000 attributes and 314 MB.  Long default values, and
  several ATTLIST declarations for one element type, multiply this further.
* **Namespace expansion.**  ElementTree names every element ``{uri}local``, so
  a 20 KB ``xmlns`` URI and 5,000 distinct short element names (59 KB in all)
  became 200 MB of tag strings.
* **Tokens.**  A single multi-megabyte tag, comment or DOCTYPE literal costs
  quadratic re-parsing on libexpat below 2.6.0 (CVE-2023-52425).

A fourth hazard is checked on the built tree, which the parse itself survives:

* **Depth.**  ``<a>`` nested 100,000 deep (700 KB) parses, then crashes the
  interpreter outright in ``copy.deepcopy`` (C stack overflow, CWE-674), and
  raises ``RecursionError`` from ``tostring`` and ``pickle`` at 1,000.

The ceilings below were sized from a scan of every XML file in the NLTK data
distribution (29,112 files, 1.7 GB): the largest holds 1,244,565 elements
(``brown_tei/Corpus.xml``, 28 MB) and 1,455,870 attributes
(``alpino/alpino.xml``, 22 MB); the deepest nests 26 levels; the longest markup
token is 756 bytes; no file declares a default attribute; the longest namespace
URI is under 64 bytes; and the amplifiable cost of any file (attribute entries
and values plus distinct expanded names) never exceeds 1.02 bytes per input
byte.  Every ceiling is a module attribute a caller may raise for a trusted
document.

Why the pre-scan re-parses with expat instead of screening text
---------------------------------------------------------------
An earlier fallback screened the DOCTYPE internal subset with string walking.
That is a parser *differential* waiting to happen: a ``<!ENTITY`` hidden behind
a comment or processing instruction that the screener skips but expat still
processes slips through.  Re-parsing with :mod:`xml.parsers.expat`, the very
library ``ElementTree`` sits on, removes the differential entirely: whatever
declaration or default the real parse would act on, the pre-scan sees first.
The scan uses ElementTree's own namespace separator and feeds each input in its
own type (``str`` or ``bytes``), so both passes decode and expand identically.

The pass runs no per-element Python code unless the document can amplify: it
arms element counting only once it sees a default attribute declaration, a
namespace URI over 64 bytes, or an input large enough to reach the element
and attribute ceilings without either (an explicit element or attribute costs
at least four input bytes).  An ordinary document therefore pays one bare
expat pass plus a breadth-first walk of the built tree for depth, together
a fifth to a third of the tree build on the largest real corpora.
"""

import io
from xml.etree import ElementTree
from xml.parsers import expat

from nltk.pathsec import open as pathsec_open
from nltk.pathsec import validate_path

__all__ = [
    "HAVE_DEFUSEDXML",
    "EntitiesForbidden",
    "StructureForbidden",
    "MAX_ELEMENTS",
    "MAX_ATTRIBUTES",
    "MAX_DEPTH",
    "MAX_TOKEN_BYTES",
    "MAX_EXPANSION",
    "fromstring",
    "parse",
]

try:
    from defusedxml import EntitiesForbidden, ExternalReferenceForbidden
    from defusedxml.ElementTree import fromstring as _defused_fromstring
    from defusedxml.ElementTree import parse as _defused_parse

    HAVE_DEFUSEDXML = True
except ImportError:  # pragma: no cover - exercised only without defusedxml
    HAVE_DEFUSEDXML = False

    class EntitiesForbidden(ValueError):
        """Raised when a document declares or references an XML entity.

        Mirrors ``defusedxml.common.EntitiesForbidden``, which is likewise a
        ``ValueError``, so ``except ValueError`` catches either back end.
        """

        def __init__(self, name="", *args):
            self.name = name
            super().__init__(
                f"XML entity declaration forbidden: {name or '<unnamed>'}. "
                "Entity expansion can exhaust memory (CWE-776); if this "
                "document is trusted, parse it with xml.etree.ElementTree "
                "directly."
            )

    ExternalReferenceForbidden = None


#: Most elements one document may hold (the largest real NLTK file has 1.25M).
MAX_ELEMENTS = 20_000_000
#: Most attributes, DTD defaults included (the largest real file has 1.46M).
MAX_ATTRIBUTES = 20_000_000
#: Deepest element nesting (real data nests 26 levels; libxml2 refuses 256).
MAX_DEPTH = 1_000
#: Longest single markup token: a tag with its attributes, a comment, a
#: processing instruction or a DOCTYPE literal (real data: 756 bytes).  The
#: feed is cut where a pending token would pass it, so a token one byte over
#: is refused on every expat version; text and CDATA runs are not tokens.
MAX_TOKEN_BYTES = 1024 * 1024
#: Most bytes of attribute entries, attribute values and distinct expanded
#: names the tree may hold per input byte (real data: 1.02).
MAX_EXPANSION = 16

# What one attribute entry costs the tree before its value: a dict slot and
# the value object.  An explicit attribute pays at least four input bytes.
_ATTRIBUTE_COST = 8
# A namespace URI this long, over many distinct short names, can outrun
# MAX_EXPANSION; a shorter one cannot (real URIs are under 64 bytes).
_LONG_NAMESPACE = 64
_STEP = 64 * 1024


class StructureForbidden(ValueError):
    """Raised when a document's parsed form would exceed a ceiling above.

    A ``ValueError``, like ``EntitiesForbidden``, so ``except ValueError``
    catches every refusal this module makes.
    """


def _refuse(what, limit):
    raise StructureForbidden(
        f"XML document refused: {what} exceeds {limit} (CWE-400). Building the "
        "tree would cost far more than the bytes that describe it; raise the "
        "matching nltk.xmlsec.MAX_* ceiling if this document is trusted."
    )


def _screen(data):
    """Refuse (raise) if ``data`` declares an entity or would exceed a ceiling.

    Runs a standalone streaming expat parse that builds no tree.  Its entity
    handlers raise on the first declaration or external reference.  The chunk
    loop bounds the longest markup token from what expat has left unconsumed.
    Once the document shows it can amplify (a default attribute declaration, a
    long namespace URI, or an input big enough to reach the count ceilings on
    its own) an element handler is armed that counts elements and attributes
    (DTD defaults included) and charges expanded names and attribute values
    against the bytes fed so far.  ``data`` is fed in its own type (``str`` or
    ``bytes``) so the scan and the real parse decode identically.  A malformed
    document raises ``ExpatError`` here; that is left for the real parse to
    report so the error matches a direct parse, and it is not exploitable
    because nothing past the error is ever built.
    """
    parser = expat.ParserCreate(None, "}")
    parser.ordered_attributes = True
    elements = attributes = cost = fed = 0
    names = set()
    armed = False

    def _start(name, attrs):
        nonlocal elements, attributes, cost
        elements += 1
        if name not in names:
            names.add(name)
            cost += len(name)
        if attrs:
            attributes += len(attrs) >> 1
            for i in range(0, len(attrs), 2):
                aname = attrs[i]
                if aname not in names:
                    names.add(aname)
                    cost += len(aname)
                cost += _ATTRIBUTE_COST + len(attrs[i + 1])
        if (
            elements > MAX_ELEMENTS
            or attributes > MAX_ATTRIBUTES
            or cost > MAX_EXPANSION * fed
        ):
            if elements > MAX_ELEMENTS:
                _refuse("its element count", f"{MAX_ELEMENTS} elements")
            if attributes > MAX_ATTRIBUTES:
                _refuse(
                    "its attribute count, DTD defaults included",
                    f"{MAX_ATTRIBUTES} attributes",
                )
            _refuse(
                "the attributes and expanded names its tree would hold",
                f"{MAX_EXPANSION} bytes per input byte",
            )

    def _arm():
        nonlocal armed
        if not armed:
            armed = True
            parser.StartElementHandler = _start

    def _attlist(elname, attname, atype, default, required):
        if default is not None:
            _arm()

    def _namespace(prefix, uri):
        if uri is not None and len(uri) > _LONG_NAMESPACE:
            _arm()

    def _forbid_declaration(name, is_parameter, value, base, sysid, pubid, notation):
        raise EntitiesForbidden(name, value, base, sysid, pubid, notation)

    def _forbid_external(context, base, sysid, pubid):
        if ExternalReferenceForbidden is not None:
            raise ExternalReferenceForbidden(context, base, sysid, pubid)
        raise EntitiesForbidden("external")

    parser.AttlistDeclHandler = _attlist
    parser.StartNamespaceDeclHandler = _namespace
    parser.EntityDeclHandler = _forbid_declaration
    parser.ExternalEntityRefHandler = _forbid_external

    text = isinstance(data, str)
    # An explicit element or attribute costs at least four input bytes, so a
    # smaller input cannot reach either count ceiling without defaults.
    if len(data) > 4 * min(MAX_ELEMENTS, MAX_ATTRIBUTES):
        _arm()
    mark = 0
    offset, end = 0, len(data)
    try:
        while offset < end:
            # Feed no further than the point where the markup token expat still
            # holds would pass the ceiling, so the check below fires exactly
            # there: an expat without reparse deferral (before 2.6) otherwise
            # completes a slightly longer token inside the next chunk unseen.
            room = MAX_TOKEN_BYTES + 1 - (fed - mark)
            chunk = data[offset : offset + max(1, min(_STEP, room))]
            offset += len(chunk)
            if text:
                encoded = chunk.encode("utf-8")
                if len(encoded) > room:
                    # The slice counted characters and the ceiling counts bytes:
                    # keep the longest prefix within room, at least one whole
                    # character, so a multibyte token is cut where an ASCII one is.
                    cut = room
                    while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
                        cut -= 1
                    kept = encoded[:cut].decode("utf-8") if cut else chunk[0]
                    offset -= len(chunk) - len(kept)
                    chunk, encoded = kept, kept.encode("utf-8")
                fed += len(encoded)
                parser.Parse(chunk, False)
            else:
                chunk = bytes(chunk)
                fed += len(chunk)
                parser.Parse(chunk, False)
            # Between calls expat reports where the unfinished markup token
            # it still holds begins, or -1 while it defers re-parsing that
            # same token; either way the last start seen bounds its length.
            consumed = parser.CurrentByteIndex
            if consumed >= 0:
                mark = consumed
            if fed - mark > MAX_TOKEN_BYTES:
                _refuse("a single markup token", f"{MAX_TOKEN_BYTES} bytes")
        parser.Parse("" if text else b"", True)
    except expat.ExpatError:
        # Not well-formed: defer to the real parse, which raises its own
        # ParseError on the same input and builds nothing past that point.
        pass


def _check_tree(root):
    """Refuse a built tree nested deeper than ``MAX_DEPTH`` or holding more
    elements than ``MAX_ELEMENTS``.  Breadth-first, one level per list, so
    the walk itself never recurses and touches no element's attributes."""
    level = [root]
    depth = elements = 0
    while level:
        depth += 1
        if depth > MAX_DEPTH:
            _refuse("its nesting depth", f"{MAX_DEPTH} levels")
        elements += len(level)
        if elements > MAX_ELEMENTS:
            _refuse("its element count", f"{MAX_ELEMENTS} elements")
        level = [child for element in level for child in element]


def _reject_entities(data):
    """Raise if ``data`` declares/refers an entity or exceeds a ceiling.

    Kept as the name the fallback pre-scan has always had; :func:`_screen`
    does the work for both back ends.
    """
    _screen(data)


def fromstring(text):
    """``ElementTree.fromstring`` that refuses entities and bounds the tree."""
    _screen(text)
    if HAVE_DEFUSEDXML:
        root = _defused_fromstring(text)
    else:
        root = ElementTree.fromstring(text)
    _check_tree(root)
    return root


def parse(source):
    """``ElementTree.parse`` that refuses entities and bounds the tree.

    ``source`` may be a filename or a file object.  A file object is read in
    full so it can be screened before parsing; ``ElementTree.parse`` reads it
    to the end regardless, so nothing is lost.
    """
    # A filename source is caller-controlled: validate it before either back end
    # sees it (CWE-22), then read it through pathsec.  A file object has no path.
    if hasattr(source, "read"):
        data = source.read()
    else:
        validate_path(source, context="nltk.xmlsec.parse")
        with pathsec_open(source, "rb", context="xmlsec.parse") as stream:
            data = stream.read()

    _screen(data)
    buffer = io.StringIO(data) if isinstance(data, str) else io.BytesIO(data)
    if HAVE_DEFUSEDXML:
        tree = _defused_parse(buffer)
    else:
        tree = ElementTree.parse(buffer)
    _check_tree(tree.getroot())
    return tree
