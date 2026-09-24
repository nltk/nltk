# Natural Language Toolkit: SeekableUnicodeStreamReader.readline accumulation tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``readline`` collects the spans of a long line in a list and joins once a
break appears (or at end of stream). Growing a ``str`` in place copied the
whole buffer on every 8000-character pass on Windows, the residual quadratic
the GHSA-j8g8 probe caught there (CWE-407). These pins hold the rewrite to the
old behaviour byte for byte across every seam the loop has: a CR LF split at a
read boundary, a leftover partial line in ``linebuffer``, the ``size``
argument, every Unicode line boundary, and random line mixes checked against
``str.splitlines``."""

import io
import random

import pytest

from nltk.data import SeekableUnicodeStreamReader

_BOUNDARIES = ["\n", "\r", "\r\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "
", "
"]


def _lines(text, **kwargs):
    reader = SeekableUnicodeStreamReader(io.BytesIO(text.encode("utf-8")), "utf-8")
    out = []
    while True:
        line = reader.readline(**kwargs)
        if not line:
            return out
        out.append(line)


def _reference_lines(text):
    # the reader splits on every str.splitlines boundary (not just CR / LF, as
    # io.StringIO does), so the oracle is splitlines itself
    return text.splitlines(keepends=True)


@pytest.mark.parametrize("offset", [71, 72, 73, 143, 144, 145, 7999, 8000, 8001])
def test_crlf_split_at_a_read_boundary_stays_one_line(offset):
    # readsize starts at 72 and doubles to 8000: a CR landing on the last
    # character of a span must still pair with the LF of the next one
    text = "a" * offset + "\r\n" + "b" * 10 + "\n"
    assert _lines(text) == ["a" * offset + "\r\n", "b" * 10 + "\n"]


@pytest.mark.parametrize("boundary", _BOUNDARIES)
def test_every_unicode_line_boundary_splits(boundary):
    text = "first" + boundary + "second" + boundary
    assert _lines(text) == ["first" + boundary, "second" + boundary]


def test_leftover_partial_line_is_prepended():
    # a partial last line left in linebuffer by an earlier split must head
    # the next readline result, unchanged
    text = "one\ntwo\nthree-without-end"
    reader = SeekableUnicodeStreamReader(io.BytesIO(text.encode()), "utf-8")
    assert reader.readline() == "one\n"
    assert reader.readline() == "two\n"
    assert reader.readline() == "three-without-end"
    assert reader.readline() == ""


def test_size_argument_returns_at_most_that_many_bytes():
    reader = SeekableUnicodeStreamReader(io.BytesIO(b"abcdefghij\nrest\n"), "utf-8")
    assert reader.readline(size=4) == "abcd"
    assert reader.readline() == "efghij\n"


def test_unterminated_line_is_returned_whole():
    text = "x" * 200_000
    assert _lines(text) == [text]


@pytest.mark.parametrize("seed", range(8))
def test_random_line_mixes_are_byte_identical_to_splitlines(seed):
    rng = random.Random(seed)
    pieces = []
    for _ in range(rng.randint(1, 60)):
        pieces.append("".join(rng.choice("ab cdé") for _ in range(rng.randint(0, 300))))
        pieces.append(rng.choice(_BOUNDARIES))
    if rng.random() < 0.5:
        pieces.append("tail-without-newline")
    text = "".join(pieces)
    assert _lines(text) == _reference_lines(text)


def test_readline_never_grows_a_str_in_place():
    import inspect
    import re

    src = inspect.getsource(SeekableUnicodeStreamReader.readline)
    # the growing buffer must never be extended in place; the one-character
    # CR LF pairing on new_chars is not the buffer
    assert not re.search(r"^\s*chars \+=", src, re.M)
    assert '"".join(parts)' in src
