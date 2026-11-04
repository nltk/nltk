# Natural Language Toolkit: jsontags depth scan and non-finite walk tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The jsontags depth scan and non-finite walk must decide as references do.

* The depth scan resolves escapes before it deletes the other bytes; it is
  checked against a byte-by-byte reference on every small text.
* The non-finite walk is checked against a full walk on every small container
  and on weight-shaped documents with a non-finite value anywhere.
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


def test_depth_scan_matches_the_byte_by_byte_reference():
    """On every text over the structural bytes up to length 7, and over them
    plus a backslash and a letter up to length 6, the scan equals the byte by
    byte reference wherever the parser could read the text, and is never below
    the depth the parser reaches before it stops."""
    for text in _texts():
        depth, sound = _reference_depth(text)
        got = _utf8_depth(text, 10**9)
        assert got >= sound, text
        if _no_stray_backslash(text):
            assert got == depth, text


@pytest.mark.parametrize("step", [1, 2, 3])
def test_depth_scan_in_steps_matches_the_byte_by_byte_reference(step, monkeypatch):
    """The same texts read in steps of one to three bytes, so that every run of
    backslashes and every escape is split between two steps somewhere, scan
    exactly as they do whole."""
    monkeypatch.setattr("nltk.jsontags._READ_STEP", step)
    for text in _texts():
        depth, sound = _reference_depth(text)
        got = _utf8_depth(text, 10**9)
        assert got >= sound, (step, text)
        if _no_stray_backslash(text):
            assert got == depth, (step, text)


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


def _weights(n, bad=None, at=0):
    """A weights-shaped document, a dict of n dicts of floats, with ``bad``
    (a JSON literal) as one weight of the ``at``-th feature."""
    feats = []
    for i in range(n):
        tags = '"NN": 0.5, "VB": -0.25'
        if bad is not None and i == at:
            tags += f', "JJ": {bad}'
        feats.append(f'"f{i}": {{{tags}}}')
    return "{" + ", ".join(feats) + "}"


_BAD = ["NaN", "Infinity", "-Infinity", "1e400", "-1e400"]


@pytest.mark.parametrize(
    "doc",
    [
        '{"f": {"NN": 0.5, "VB": NaN}}',
        '{"f": {"NN": 0.5}, "g": {"VB": -Infinity}}',
        "[[1.0, 2.0], [3.0, 1e400]]",
        '{"f": {"NN": 1e308, "VB": 1e308, "JJ": Infinity}}',
    ]
    + [_weights(200, bad, at) for bad in _BAD for at in (0, 117, 199)]
    + ["[" + ", ".join(["0.5"] * 100 + [bad]) + "]" for bad in _BAD]
    + ["[" + ", ".join([bad] + ["0.5"] * 100) + "]" for bad in _BAD],
)
def test_non_finite_weight_is_still_refused(doc):
    """Small documents, weight dicts of 200 features with a non-finite weight
    at the first, a middle and the last feature, and long float lists with one
    at either end, are all refused."""
    with pytest.raises(ValueError, match="non-finite"):
        safe_json_loads(doc)


def test_large_finite_weights_load_as_parsed():
    for doc in (_weights(200), "[" + ", ".join(["1e308"] * 100) + "]"):
        assert safe_json_loads(doc) == json.loads(doc)


def test_finite_weights_whose_sum_overflows_still_load():
    doc = '{"f": {"NN": 1e308, "VB": 1e308}, "g": [1.7e308, 1.7e308]}'
    assert safe_json_loads(doc) == json.loads(doc)
