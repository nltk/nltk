"""Regression tests for TokenSearcher.findall query handling.

``TokenSearcher.findall`` compiles a caller-supplied query through ``nltk.redos``.
redos already reports a match-time blow-up as ``TimeoutError``; it also refuses a
source larger than ``MAX_PATTERN_LENGTH`` at compile time (``ValueError``, or
``redos.error`` for a malformed query). An oversized or invalid query must be
reported as a bad query rather than surfacing the raw refusal as an uncaught
exception; ordinary queries are unaffected.
"""

import pytest

import nltk.redos as redos
from nltk.text import TokenSearcher


def _searcher():
    return TokenSearcher("a b a c a b d".split())


def test_ordinary_query_returns_matches():
    hits = _searcher().findall("<a>(<.>)")
    assert isinstance(hits, list)
    assert hits  # the query matches, so at least one hit


def test_oversized_query_is_a_clean_error():
    oversized = "<" + "a" * (redos.MAX_PATTERN_LENGTH + 10) + ">"
    with pytest.raises(ValueError):
        _searcher().findall(oversized)
