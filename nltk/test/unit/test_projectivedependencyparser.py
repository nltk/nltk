"""Regression tests for the quadratic-memory / cubic-time DoS in
``nltk.parse.projectivedependencyparser`` (CWE-407).

Both ``ProjectiveDependencyParser`` and ``ProbabilisticProjectiveDependencyParser``
eagerly build a dense ``(n+1)x(n+1)`` chart (O(n^2) memory) and run an
unconditional triple loop over it (O(n^3) time), regardless of the grammar -- so
a short list of a few hundred/thousand tokens pins a CPU core and exhausts
memory. ``parse`` now refuses with a ``ValueError`` once the token count exceeds
the configurable ``MAX_TOKENS``, before any chart is allocated; ordinary
sentence-length parses are unchanged.
"""

import pytest

from nltk.grammar import DependencyGrammar
from nltk.parse.projectivedependencyparser import (
    ProbabilisticProjectiveDependencyParser,
    ProjectiveDependencyParser,
)

_GRAMMAR = DependencyGrammar.fromstring(
    """
    'fell' -> 'price' | 'stock'
    'price' -> 'of' | 'the'
    'of' -> 'stock'
    'stock' -> 'the'
    """
)
_SENTENCE = ["the", "price", "of", "the", "stock", "fell"]


def test_default_max_tokens_is_positive_int():
    assert isinstance(ProjectiveDependencyParser.MAX_TOKENS, int)
    assert ProjectiveDependencyParser.MAX_TOKENS > 0
    assert isinstance(ProbabilisticProjectiveDependencyParser.MAX_TOKENS, int)
    assert ProbabilisticProjectiveDependencyParser.MAX_TOKENS > 0


def test_projective_parse_preserves_results():
    """An ordinary sentence parses to the same trees as before."""
    parser = ProjectiveDependencyParser(_GRAMMAR)
    trees = list(parser.parse(_SENTENCE))
    assert len(trees) == 3
    assert "(fell (price the of the) stock)" in [str(t) for t in trees]


def test_projective_parse_accepts_generator_input():
    """A non-subscriptable iterable (generator) parses like a list.

    parse() materializes the input with list(...) but later indexes tokens[i]
    when building output; the local name is rebound to the materialized list so
    an iterator/generator input does not raise TypeError.
    """
    parser = ProjectiveDependencyParser(_GRAMMAR)
    trees = list(parser.parse(iter(_SENTENCE)))
    assert len(trees) == 3
    assert "(fell (price the of the) stock)" in [str(t) for t in trees]


def test_projective_parse_rejects_over_cap():
    """Over the default cap, parse refuses instead of building the chart."""
    parser = ProjectiveDependencyParser(DependencyGrammar.fromstring("'x' -> 'y'"))
    n = ProjectiveDependencyParser.MAX_TOKENS + 1
    with pytest.raises(ValueError, match="MAX_TOKENS"):
        list(parser.parse(["a"] * n))


def test_projective_parse_respects_lowered_cap():
    """MAX_TOKENS is tunable per instance; at/under the cap still parses."""
    parser = ProjectiveDependencyParser(DependencyGrammar.fromstring("'x' -> 'y'"))
    parser.MAX_TOKENS = 3
    with pytest.raises(ValueError, match="MAX_TOKENS"):
        list(parser.parse(["a", "a", "a", "a"]))
    # exactly at the cap is allowed (no match -> empty result, but no error).
    assert list(parser.parse(["a", "a", "a"])) == []


def test_probabilistic_parse_rejects_over_cap():
    """The probabilistic decoder enforces the cap before touching the grammar."""
    parser = ProbabilisticProjectiveDependencyParser()
    parser.MAX_TOKENS = 4
    with pytest.raises(ValueError, match="MAX_TOKENS"):
        list(parser.parse(["a"] * 5))
