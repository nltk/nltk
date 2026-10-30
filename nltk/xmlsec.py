# -*- coding: utf-8 -*-
# Natural Language Toolkit: Bounded, entity-free XML parsing
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
XML parsing for the 3.4 maintenance line, named as in the 3.10 line's
``nltk.xmlsec``: :func:`parse` and :func:`fromstring` replace
``ElementTree.parse`` and ``ElementTree.fromstring`` at every sink.

A document can neither expand (entity declarations are refused: billion
laughs, CWE-776) nor fetch (external references are refused: XXE, CWE-611),
and the tree it builds is bounded in depth and size (CWE-674, CWE-400).
``defusedxml`` is used when installed; otherwise a small expat tree builder
applies the same refusals, because the stock ``XMLParser`` on Python 3 hides
its expat parser. The 3.10 module also screens tokens and expansion ratios
before building; this line keeps the refusals and the tree bounds.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import io
from xml.etree import ElementTree as _ElementTree
from xml.parsers import expat as _expat

from six import PY2, binary_type, text_type

__all__ = [
    "EntitiesForbidden",
    "StructureForbidden",
    "MAX_ELEMENTS",
    "MAX_DEPTH",
    "MAX_BYTES",
    "parse",
    "fromstring",
]

#: Ceilings on a parsed document, as in the 3.10 line.
MAX_ELEMENTS = 20000000
MAX_DEPTH = 1000
#: Largest document read from a path or stream.
MAX_BYTES = 1024 * 1024 * 1024

try:  # the vendor library when installed; the expat fence below otherwise
    import defusedxml.ElementTree as _defused_etree
except ImportError:  # pragma: no cover
    _defused_etree = None


class EntitiesForbidden(ValueError):
    """Raised for an entity declaration or an external reference."""


class StructureForbidden(ValueError):
    """Raised for a tree deeper or larger than the ceilings allow."""


def _fenced_expat_parse(data):
    """Build an ElementTree from *data* with an expat parser whose entity
    and external-reference handlers refuse. Names come out in ElementTree's
    ``{uri}local`` form; on 2.7 ASCII-only content is a native ``str``, as the
    2.7 ElementTree parser produced it."""
    builder = _ElementTree.TreeBuilder()
    parser = _expat.ParserCreate(None, "}")
    parser.ordered_attributes = True
    parser.buffer_text = True

    def fixtext(text):
        if PY2 and isinstance(text, text_type):
            try:
                return text.encode("ascii")
            except UnicodeEncodeError:
                return text
        return text

    def fix(name):
        return fixtext("{" + name if "}" in name else name)

    def start(name, attrs):
        attrib = {}
        for i in range(0, len(attrs), 2):
            attrib[fix(attrs[i])] = fixtext(attrs[i + 1])
        builder.start(fix(name), attrib)

    def forbid_entity(name, is_parameter, value, base, sysid, pubid, notation):
        raise EntitiesForbidden("entity declarations are not allowed (%r)" % (name,))

    def forbid_external(context, base, sysid, pubid):
        raise EntitiesForbidden("external entity references are not allowed")

    def forbid_unparsed(name, base, sysid, pubid, notation):
        raise EntitiesForbidden("unparsed entity declarations are not allowed")

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: builder.end(fix(name))
    parser.CharacterDataHandler = lambda data: builder.data(fixtext(data))
    parser.EntityDeclHandler = forbid_entity
    parser.UnparsedEntityDeclHandler = forbid_unparsed
    parser.ExternalEntityRefHandler = forbid_external
    try:
        parser.Parse(data, True)
    except _expat.ExpatError as exc:
        raise _ElementTree.ParseError(str(exc))
    return builder.close()


def _check_tree(root):
    """Refuse a tree deeper than ``MAX_DEPTH`` or larger than ``MAX_ELEMENTS``."""
    count = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > MAX_DEPTH:
            raise StructureForbidden("XML nested deeper than %d elements" % MAX_DEPTH)
        if count > MAX_ELEMENTS:
            raise StructureForbidden("XML holds more than %d elements" % MAX_ELEMENTS)
        for child in list(node):
            stack.append((child, depth + 1))
    return root


def _read_source(source):
    if hasattr(source, "read"):
        data = source.read(MAX_BYTES + 1)
    else:
        with io.open(source, "rb") as fh:
            data = fh.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise StructureForbidden("XML document exceeds %d bytes" % MAX_BYTES)
    return data


def parse(source):
    """``ElementTree.parse`` that refuses entities and external references
    and bounds the tree it builds. *source* is a path or a binary stream."""
    if _defused_etree is not None:
        tree = _defused_etree.parse(source, forbid_dtd=False, forbid_entities=True, forbid_external=True)
        _check_tree(tree.getroot())
        return tree
    root = _fenced_expat_parse(_read_source(source))
    return _ElementTree.ElementTree(_check_tree(root))


def fromstring(text):
    """``ElementTree.fromstring`` with the same refusals and bounds."""
    if _defused_etree is not None:
        root = _defused_etree.fromstring(text, forbid_dtd=False, forbid_entities=True, forbid_external=True)
        return _check_tree(root)
    if isinstance(text, text_type):
        text = text.encode("utf-8")
    return _check_tree(_fenced_expat_parse(text))
