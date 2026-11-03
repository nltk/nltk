# Natural Language Toolkit: JSON depth pre-scan regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The JSON depth pre-scan must count the nesting the parser will recurse into.

``safe_json_loads`` and ``JSONTaggedDecoder`` refuse a document nested deeper
than their cap BEFORE the recursive C decoder sees it: on Python 3.11 with a
raised recursion limit the decoder overflows the C stack (a segfault) on deep
input. Two inputs made the scan report a depth of 1 for a document of any
depth:

* an escape other than ``\\"`` or ``\\\\`` (``"\\n"``): the scan deleted the
  escaped letter first, so the backslash swallowed the closing quote and every
  bracket up to the next quote counted as string content;
* ``bytes`` in UTF-16 or UTF-32, which ``json.loads`` decodes itself: the scan
  read the raw bytes, where U+4E22 is ``22 4E`` in UTF-16-LE, a stray quote.

Every attack runs the real chokepoint and asserts its depth refusal; every
benign twin loads and equals ``json.loads``. The space of small documents is
enumerated exhaustively, never sampled.
"""

import itertools
import json
import os
import subprocess
import sys

import pytest

from nltk.jsontags import (
    JSON_MAX_DEPTH,
    JSONTaggedDecoder,
    _scan_json_depth,
    safe_json_loads,
)

_REFUSED = "nesting depth exceeds"


def _nested(depth):
    return "[" * depth + "]" * depth


# A string value before the nesting, for every escape JSON defines and for the
# characters that hide a quote or bracket byte inside a UTF-16/32 code unit.
_ESCAPES = ["\\n", "\\t", "\\r", "\\b", "\\f", "\\/", "\\u0041", '\\"', "\\\\"]
_HIDING_CHARS = [chr(0x4E22), chr(0x225B), chr(0x5B5D), chr(0x7B7D), chr(0x2222)]


def _attack_docs(depth):
    for esc in _ESCAPES:
        yield f"esc{esc!r}", '["' + esc + '", ' + _nested(depth) + "]"
        yield f"key{esc!r}", '{"' + esc + '": ' + _nested(depth) + "}"
    for ch in _HIDING_CHARS:
        yield f"char{ord(ch):04x}", '["' + ch + '", ' + _nested(depth) + "]"


_ENCODINGS = [
    "utf-8",
    "utf-8-sig",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "utf-32",
    "utf-32-le",
    "utf-32-be",
]


def _forms(doc):
    yield "str", doc
    for enc in _ENCODINGS:
        yield enc, doc.encode(enc)


@pytest.mark.parametrize("name,doc", list(_attack_docs(JSON_MAX_DEPTH + 1)))
def test_deep_document_after_any_string_is_refused(name, doc):
    for form, data in _forms(doc):
        with pytest.raises(ValueError, match=_REFUSED):
            safe_json_loads(data)
        assert _scan_json_depth(data, 10**9) == JSON_MAX_DEPTH + 2, form


@pytest.mark.parametrize("name,doc", list(_attack_docs(3)))
def test_shallow_twin_loads_unchanged(name, doc):
    for form, data in _forms(doc):
        assert safe_json_loads(data) == json.loads(data), form
        assert _scan_json_depth(data, 10**9) == 4, form


def test_tagged_decoder_counts_after_an_escape():
    deep = '["\\n", ' + _nested(JSONTaggedDecoder.MAX_DECODE_DEPTH + 1) + "]"
    with pytest.raises(ValueError, match="nesting depth exceeds"):
        json.loads(deep, cls=JSONTaggedDecoder)
    assert json.loads('["\\n", [[1]]]', cls=JSONTaggedDecoder) == ["\n", [[1]]]


_CHILD = r"""
import sys
from nltk.jsontags import safe_json_loads
sys.setrecursionlimit(1_000_000)
n = 300_000
doc = '["\\n", ' + "[" * n + "]" * n + "]"
try:
    safe_json_loads(doc.encode(sys.argv[1]) if sys.argv[1] != "str" else doc)
except ValueError as exc:
    print("REFUSED", exc)
"""


@pytest.mark.parametrize("form", ["str", "utf-8", "utf-16-le"])
def test_hidden_deep_document_cannot_crash_a_raised_recursion_limit(form):
    """The crash the cap exists for: with the recursion limit raised, a
    300,000-deep document the scan missed reached the C decoder, which
    segfaults on Python 3.11. The scan must refuse it with its own message."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, form],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, (proc.returncode, proc.stderr[-500:])
    assert "REFUSED" in proc.stdout and _REFUSED in proc.stdout, proc.stdout


def _depth(obj):
    if isinstance(obj, list):
        return 1 + max((_depth(v) for v in obj), default=0)
    if isinstance(obj, dict):
        return 1 + max((_depth(v) for v in obj.values()), default=0)
    return 0


# String literals that put quotes, backslashes and brackets inside strings.
_LEAF_STRINGS = [
    '""',
    '"a"',
    '"\\\\"',
    '"\\""',
    '"\\\\\\""',
    '"[\\"]"',
    '"\\n["',
    '"]}"',
    '"\\\\\\\\"',
    '"{\\u0022["',
]


def _documents(levels):
    """Every JSON document over the leaf strings and the number 1 built from
    lists and single-key objects of up to two members, nested ``levels`` deep."""
    if levels == 0:
        yield from _LEAF_STRINGS + ["1"]
        return
    smaller = list(_documents(levels - 1))
    yield from smaller
    for a in smaller:
        yield "[" + a + "]"
        yield '{"k":' + a + "}"
    for a, b in itertools.product(smaller[:12], repeat=2):
        yield "[" + a + "," + b + "]"
        yield "{" + _LEAF_STRINGS[5] + ":" + a + "," + _LEAF_STRINGS[3] + ":" + b + "}"


def test_scan_equals_true_depth_on_every_small_document():
    """On every enumerated document, in every form the parser accepts, the
    scan reports exactly the depth the parser builds: never less (a bypass),
    never more (a refused legitimate document)."""
    seen = 0
    for doc in set(_documents(3)):
        expected = _depth(json.loads(doc))
        for form, data in _forms(doc):
            assert _scan_json_depth(data, 10**9) == expected, (form, doc)
        seen += 1
    assert seen > 1000
