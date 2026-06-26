"""Regression tests for the exponential chart-parsing DoS (CWE-770; CVE-2026-12886).

A highly-ambiguous grammar such as the 15-byte ``S -> S S | 'a'`` makes the
number of parses exponential in the sentence length (the Catalan numbers), and
``nltk.parse.chart`` materialises every parse tree eagerly while reading them off
the chart -- so a tiny grammar plus a short sentence pins the CPU and exhausts
memory, and even obtaining the first parse never returns. The number of parse-tree
nodes built is now bounded by ``MAX_PARSE_TREES``; once exceeded, tree extraction
raises ``ValueError``.

The "must not run unbounded" test runs in a spawned process with a hard timeout,
and the worker reports its outcome via its exit code (no queue/thread, so it is
robust on free-threaded builds), so a regression cannot hang the suite.
"""

import multiprocessing
import os

import pytest

from nltk import CFG
from nltk.parse import BottomUpChartParser, ChartParser
from nltk.parse import chart as chart_mod
from nltk.parse.chart import MAX_PARSE_TREES

_AMBIG = CFG.fromstring("S -> S S | 'a'")  # 15 bytes, Catalan-many parses


def test_max_parse_trees_is_a_finite_positive_int():
    assert isinstance(MAX_PARSE_TREES, int)
    assert MAX_PARSE_TREES > 0


def test_parses_preserved():
    # An ordinarily-ambiguous sentence still yields all of its parses.
    g = CFG.fromstring(
        "S -> NP VP\n"
        "NP -> 'I' | 'a' N | NP PP\n"
        "VP -> V NP | VP PP\n"
        "PP -> P NP\n"
        "N -> 'dog' | 'park'\n"
        "V -> 'saw'\n"
        "P -> 'in'"
    )
    parses = list(ChartParser(g).parse("I saw a dog in a park".split()))
    assert len(parses) == 2  # the two PP-attachment readings

    # The Catalan parse forest is produced in full while it stays under the cap.
    p = BottomUpChartParser(_AMBIG)
    assert len(list(p.parse(["a"] * 6))) == 42  # Catalan(5)
    assert len(list(p.parse(["a"] * 10))) == 4862  # Catalan(9)


def test_over_cap_extraction_is_refused(monkeypatch):
    # With a tiny cap, an ambiguous parse forest that exceeds it is refused.
    # In process and safe: even without the guard this builds only a few hundred
    # trees, so the missing exception is detected rather than exhausting memory.
    monkeypatch.setattr(chart_mod, "MAX_PARSE_TREES", 100)
    with pytest.raises(ValueError):
        list(BottomUpChartParser(_AMBIG).parse(["a"] * 8))  # Catalan(7) = 429 > 100


_TIMEOUT = 60
_EXIT_REFUSED = 0  # ValueError raised before building the full forest (expected)
_EXIT_BUILT = 2  # the exponential forest was materialised (regression)
_EXIT_OTHER = 3


def _parse_worker():
    # 14 tokens of the ambiguous grammar: the default cap refuses this after
    # ~the cap's worth of trees (bounded memory), but without the guard it builds
    # the full forest. The size is chosen so even a guard-removed run stays well
    # under ~1 GB, so a regression is caught by the exit code (or the timeout)
    # without an OS OOM kill.
    try:
        list(BottomUpChartParser(_AMBIG).parse(["a"] * 14))
        os._exit(_EXIT_BUILT)
    except ValueError:
        os._exit(_EXIT_REFUSED)
    except BaseException:
        os._exit(_EXIT_OTHER)


def test_exponential_grammar_is_refused_not_run():
    """The default cap must refuse an exponential parse forest, not build it."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_parse_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "chart tree extraction did not finish -> unbounded exponential DoS"
        )
    assert proc.exitcode == _EXIT_REFUSED, (
        "an exponential parse forest was not refused "
        f"(worker exit code {proc.exitcode})"
    )
