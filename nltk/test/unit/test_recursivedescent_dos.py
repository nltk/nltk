"""
Regression tests for the RecursiveDescentParser wall-clock DoS bound
(CVE-2026-12876 / GHSA-ff5c-cp5c-9wjf).

Top-down recursive-descent search is unbounded on a left-recursive or highly
ambiguous grammar: a tiny crafted grammar makes a short input consume CPU
forever (CWE-407 / CWE-674). Both payloads below were reproduced hanging on the
unpatched parser (killed after 8s on a 24-token input). The fix arms a
wall-clock deadline on the first parse step and checks it on every recursive
entry, raising ``TimeoutError`` when exceeded; ``max_time=None`` disables it.

``max_time`` is a Python-level check (not subject to the ``re``-style GIL
problem), so the exploits raise in-process and the tests need no subprocess.
"""

import time

import pytest

from nltk import CFG
from nltk.parse import RecursiveDescentParser
from nltk.parse.recursivedescent import DEFAULT_MAX_TIME

BENIGN = CFG.fromstring(
    """
    S -> NP VP
    NP -> 'the' N
    VP -> V NP
    N -> 'dog' | 'cat'
    V -> 'saw' | 'chased'
    """
)
#: Ambiguous grammar -> exponentially many parses; the wall-clock bound trips
#: reliably (the work is broad, not deep, so Python's recursion guard does not).
AMBIGUOUS = CFG.fromstring("S -> 'a' S | 'a' S S | 'a'")
#: Left-recursive grammar -> unbounded recursion.
LEFT_RECURSIVE = CFG.fromstring("S -> S S | 'a'")


class TestRecursiveDescentDoS:
    def test_default_is_bounded_out_of_the_box(self):
        # A crafted grammar must be bounded even when the caller sets nothing --
        # the default must not be "unlimited".
        assert DEFAULT_MAX_TIME is not None
        assert 0 < DEFAULT_MAX_TIME <= 30
        assert RecursiveDescentParser(BENIGN)._max_time == DEFAULT_MAX_TIME

    def test_benign_parse_unaffected(self):
        trees = list(
            RecursiveDescentParser(BENIGN).parse(["the", "dog", "saw", "the", "cat"])
        )
        assert len(trees) == 1
        assert trees[0].label() == "S"
        assert str(trees[0]) == "(S (NP the (N dog)) (VP (V saw) (NP the (N cat))))"

    def test_ambiguous_grammar_times_out(self):
        parser = RecursiveDescentParser(AMBIGUOUS, max_time=0.5)
        start = time.perf_counter()
        with pytest.raises(TimeoutError):
            list(parser.parse(["a"] * 24))
        assert time.perf_counter() - start < 4  # bounded near max_time, not a hang

    def test_left_recursive_grammar_is_bounded(self):
        # Left recursion is unbounded work; it must not hang -- either the
        # wall-clock bound (TimeoutError) or Python's stack guard (RecursionError)
        # stops it.
        parser = RecursiveDescentParser(LEFT_RECURSIVE, max_time=0.5)
        with pytest.raises((TimeoutError, RecursionError)):
            list(parser.parse(["a"] * 24))

    def test_max_time_none_disables_the_bound(self):
        # A trusted grammar may opt out; a benign parse still works.
        parser = RecursiveDescentParser(BENIGN, max_time=None)
        assert parser._max_time is None
        assert len(list(parser.parse(["the", "dog", "saw", "the", "cat"]))) == 1
