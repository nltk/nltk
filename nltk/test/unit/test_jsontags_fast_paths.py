# Natural Language Toolkit: jsontags fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The cheaper bookkeeping in nltk.jsontags must reach the same decisions.

Two fast paths in the depth scan keep safe_json_loads close to json.loads on
model-sized input:

* the depth scan drops adjacent quote pairs from its residue before the
  Python loop, since with every escape resolved quotes alternate open and
  close, so a pair is an empty string or a close and an open with nothing
  between them;
* the brackets outside strings are counted in C (``itertools.accumulate``)
  once the residue is split on its remaining quotes.

Each is checked against a plain reference on an exhaustive enumeration of
small inputs.
"""

import itertools

import pytest

from nltk.jsontags import _utf8_depth


def _reference_depth(text):
    """JSON string state followed byte by byte on the raw text: a backslash
    inside a string escapes the next byte. Returns ``(depth, sound_depth)``:
    the maximum nesting, and the maximum before the first backslash outside a
    string, where the parser stops (it is not valid JSON there)."""
    depth = best = 0
    sound = None
    in_string = escaped = False
    for byte in text:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x5C and sound is None:
            sound = best
        if byte == 0x22:
            in_string = True
        elif byte in b"[{":
            depth += 1
            best = max(best, depth)
        elif byte in b"]}":
            depth -= 1
    return best, best if sound is None else sound


def _texts():
    for n in range(8):
        yield from (bytes(t) for t in itertools.product(b'"[]{}', repeat=n))
    for n in range(7):
        yield from (bytes(t) for t in itertools.product(b'"[]{}\\a', repeat=n))


@pytest.mark.parametrize("split_quotes", [-1, 1 << 16])
def test_depth_scan_matches_the_byte_by_byte_reference(split_quotes, monkeypatch):
    """On every text over the structural bytes up to length 7, and over them
    plus a backslash and a letter up to length 6, the scan equals the byte by
    byte reference wherever the parser could read the text, and is never below
    the depth the parser reaches before it stops; both with the residue split
    on its quotes and counted in C, and with the Python loop."""
    import nltk.jsontags as jsontags

    monkeypatch.setattr(jsontags, "_SPLIT_QUOTES", split_quotes)
    for text in _texts():
        depth, sound = _reference_depth(text)
        got = _utf8_depth(text, 10**9)
        assert got >= sound, text
        if _no_stray_backslash(text):
            assert got == depth, text


def _no_stray_backslash(text):
    in_string = escaped = False
    for byte in text:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x5C:
            return False
        elif byte == 0x22:
            in_string = True
    return True


def _reference_loop(residue, limit):
    """The Python loop the depth scan runs when a string holds a bracket."""
    depth = max_depth = 0
    in_string = False
    for byte in residue:
        if byte == 0x22:
            in_string = not in_string
        elif in_string:
            continue
        elif byte in b"[{":
            depth += 1
            if depth > max_depth:
                max_depth = depth
                if max_depth > limit:
                    return max_depth
        elif byte in b"]}":
            depth -= 1
    return max_depth


@pytest.mark.parametrize("step", [1, 2, 3, 1 << 16])
def test_bracket_count_returns_what_the_loop_returns(step, monkeypatch):
    """Brackets only (no string holds one) are counted in C, in steps; on
    every bracket string up to length 8 and every cap from -1 to past any
    depth, the count returns exactly the loop's value, early exit included."""
    import nltk.jsontags as jsontags

    monkeypatch.setattr(jsontags, "_DEPTH_STEP", step)
    lengths = range(9) if step == 1 << 16 else range(7)
    for n in lengths:
        for t in itertools.product(b"[]{}", repeat=n):
            residue = bytes(t)
            for limit in (-1, 0, 1, 2, 3, 5, 10**9):
                assert jsontags._bracket_depth(residue, limit) == _reference_loop(
                    residue, limit
                ), (residue, limit)
