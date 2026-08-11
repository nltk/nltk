# Natural Language Toolkit: Safer XML parsing.
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""XML parsing helpers that refuse entity declarations.

``xml.etree.ElementTree`` honours ``<!ENTITY>`` declarations in a document's
internal DTD subset, so a small file can expand to an arbitrarily large string
in memory -- the "billion laughs" / entity-expansion DoS (CWE-776).  A 330-byte
document expands to a megabyte with five levels of nesting, and each further
level multiplies by ten.

libexpat 2.6.0 (2024) added an input-amplification cap, but it only engages
above an activation threshold (~8 MiB of output by default) and belongs to
whatever libexpat the running interpreter links -- not to NLTK.  Builds against
an older system libexpat have no cap at all.  These helpers make the guarantee
NLTK's own.

:func:`parse` and :func:`fromstring` use ``defusedxml`` when it is installed and
fall back to an equivalent standard-library implementation when it is not, so
NLTK is protected either way and ``defusedxml`` stays an optional dependency.

External entities are *not* the concern here -- ``ElementTree`` does not resolve
them (it reports ``undefined entity``) -- but the fallback rejects them too, for
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

Why the fallback re-parses with expat instead of screening text
---------------------------------------------------------------
An earlier fallback screened the DOCTYPE internal subset with string walking.
That is a parser *differential* waiting to happen: a ``<!ENTITY`` hidden behind
a comment or processing instruction that the screener skips but expat still
processes slips through.  Re-parsing with :mod:`xml.parsers.expat` -- the very
library ``ElementTree`` sits on -- removes the differential entirely: whatever
declaration the real parse would act on, the pre-scan sees first and rejects.
The document is parsed once by expat to screen it and once by ElementTree to
build the tree; the extra pass only runs when ``defusedxml`` is absent.
(``defusedxml`` avoids the second pass by hooking ElementTree's own parser, but
only reaches it through global ``sys.modules`` surgery; the fallback keeps the
default C parser and touches no global state.)
"""

import io
from xml.etree import ElementTree
from xml.parsers import expat

__all__ = ["HAVE_DEFUSEDXML", "EntitiesForbidden", "fromstring", "parse"]

try:
    from defusedxml import EntitiesForbidden
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


def _reject_entities(data):
    """Raise :class:`EntitiesForbidden` if ``data`` declares/refers an entity.

    Runs a standalone expat parse whose entity handlers raise on the first
    declaration or external reference.  ``data`` is fed to expat in its own type
    (``str`` or ``bytes``) so the pre-scan and the real ElementTree parse decode
    identically.  A malformed document raises ``ExpatError`` here; that is left
    for ElementTree to report so the error matches a direct parse, and it is not
    exploitable because the declaration would never be reached.
    """
    parser = expat.ParserCreate()

    def _forbid_declaration(name, *rest):
        raise EntitiesForbidden(name)

    def _forbid_external(*rest):
        raise EntitiesForbidden("external")

    parser.EntityDeclHandler = _forbid_declaration
    parser.ExternalEntityRefHandler = _forbid_external
    try:
        parser.Parse(data, True)
    except expat.ExpatError:
        # Not well-formed: no entity was reached, so it cannot expand. Defer to
        # ElementTree, which raises its own ParseError on the same input.
        pass


def fromstring(text):
    """``ElementTree.fromstring`` that refuses entity declarations."""
    if HAVE_DEFUSEDXML:
        return _defused_fromstring(text)
    _reject_entities(text)
    return ElementTree.fromstring(text)


def parse(source):
    """``ElementTree.parse`` that refuses entity declarations.

    ``source`` may be a filename or a file object.  In the fallback path a file
    object is read in full so it can be screened before parsing;
    ``ElementTree.parse`` reads it to the end regardless, so nothing is lost.
    """
    if HAVE_DEFUSEDXML:
        return _defused_parse(source)

    if hasattr(source, "read"):
        data = source.read()
    else:
        with open(source, "rb") as stream:
            data = stream.read()

    _reject_entities(data)
    buffer = io.StringIO(data) if isinstance(data, str) else io.BytesIO(data)
    return ElementTree.parse(buffer)
