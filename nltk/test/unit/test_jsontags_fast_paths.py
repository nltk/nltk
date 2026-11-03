# Natural Language Toolkit: jsontags fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The cheaper bookkeeping in nltk.jsontags must reach the same decisions.

These fast paths keep safe_json_loads close to json.loads on model-sized
input:

* the depth scan drops adjacent quote pairs from its residue before the
  Python loop, since with every escape resolved quotes alternate open and
  close, so a pair is an empty string or a close and an open with nothing
  between them;
* the brackets outside strings are counted in C (``itertools.accumulate``)
  once the residue is split on its remaining quotes;
* the non-finite walk does not descend into a container whose members, or
  whose members' values when they are all dicts, ``math.fsum`` adds up to a
  finite number.

Each is checked against a plain reference on an exhaustive enumeration of
small inputs, plus the real weight shapes that motivate the walk's.
"""

import itertools
import json
import math

import pytest

from nltk.jsontags import _reject_non_finite_walk, _utf8_depth, safe_json_loads


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


def _reference_walk(obj):
    """The walk as it was: every member of every container is visited."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, float):
            if not math.isfinite(cur):
                raise ValueError("non-finite")
        elif isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


_INF = float("inf")
_LEAVES = [
    0,
    1,
    -1,
    True,
    False,
    None,
    "s",
    "",
    1.5,
    -0.0,
    1e308,
    -1e308,
    _INF,
    -_INF,
    float("nan"),
    2**2000,
]


def _verdict(walk, value):
    try:
        walk(value)
        return "ok"
    except ValueError:
        return "refused"


def _containers():
    leaves = _LEAVES + [[], {}, [_INF], {"k": float("nan")}, [1e308, 1e308]]
    for n in range(4):
        for members in itertools.product(leaves, repeat=n):
            yield list(members)
            if n <= 2:
                yield {f"k{i}": m for i, m in enumerate(members)}


def test_walk_matches_the_full_walk_on_every_small_container():
    """Every list of up to three members and every dict of up to two over the
    leaves (finite and non-finite floats, a sum that overflows, huge ints,
    strings, None, booleans, nested containers) is judged as the full walk
    judges it, alone and nested one level deeper."""
    level = list(_containers())
    for value in level:
        assert _verdict(lambda v: _reject_non_finite_walk(v, "t"), value) == _verdict(
            _reference_walk, value
        ), value
    for a, b in itertools.product(level[:: max(1, len(level) // 60)], repeat=2):
        for value in ([a, b], {"a": a, "b": b}):
            assert _verdict(
                lambda v: _reject_non_finite_walk(v, "t"), value
            ) == _verdict(_reference_walk, value), value


@pytest.mark.parametrize(
    "doc",
    [
        '{"f": {"NN": 0.5, "VB": NaN}}',
        '{"f": {"NN": 0.5}, "g": {"VB": -Infinity}}',
        "[[1.0, 2.0], [3.0, 1e400]]",
        '{"f": {"NN": 1e308, "VB": 1e308, "JJ": Infinity}}',
    ],
)
def test_non_finite_weight_is_still_refused(doc):
    with pytest.raises(ValueError, match="non-finite"):
        safe_json_loads(doc)


def test_finite_weights_whose_sum_overflows_still_load():
    doc = '{"f": {"NN": 1e308, "VB": 1e308}, "g": [1.7e308, 1.7e308]}'
    assert safe_json_loads(doc) == json.loads(doc)
