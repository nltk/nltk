"""Regression tests for the quadratic ReDoS in NLTK's token-regex search
(``nltk.text.TokenSearcher.findall`` / ``Text.findall``) -- CWE-1333.

``findall`` turned a token-regex query into a real regex and applied it
multi-position over the joined corpus with the stdlib ``re``. For a quantified
token group followed by a non-match (e.g. ``<a>*<b>`` over a long run of ``a``
tokens), ``re`` re-scanned the run from every position -- quadratic in the number
of tokens, with no bound on corpus length or backtracking. The search now uses
the third-party ``regex`` engine (which does not re-scan that way and is far
faster here) and honours a wall-clock ``timeout`` so a crafted query/corpus
cannot pin a CPU core. The output is unchanged for ordinary queries.
"""

import multiprocessing
import os
import traceback

import pytest

from nltk.text import TOKENSEARCH_TIMEOUT, Text, TokenSearcher


def test_findall_preserves_ordinary_results():
    """Ordinary token queries return the same matches as before."""
    ts = TokenSearcher("the quick brown fox the lazy dog".split())
    assert ts.findall("<the>") == [["the"], ["the"]]
    assert ts.findall("<the><.*>") == [["the", "quick"], ["the", "lazy"]]
    assert ts.findall("<no-such-token>") == []
    # quantified token group that does match
    assert TokenSearcher(["a", "a", "b", "c"]).findall("<a>*<b>") == [["a", "a", "b"]]


def test_default_timeout_is_configurable():
    """The default limit is a positive number and ``None`` disables it."""
    assert TOKENSEARCH_TIMEOUT is None or TOKENSEARCH_TIMEOUT > 0
    # timeout=None must not break a quick, ordinary search.
    assert TokenSearcher(["a", "b"]).findall("<a>*<b>", timeout=None) == [["a", "b"]]


def test_default_timeout_resolved_at_call_time(monkeypatch):
    """A runtime change to ``nltk.text.TOKENSEARCH_TIMEOUT`` affects later calls.

    The ``timeout`` default is a sentinel resolved inside ``findall``, so a
    module-level override takes effect even though the methods were defined
    earlier (a literal default would have bound the value at definition time).
    """
    import nltk.text as text_mod

    captured = {}

    def fake_findall(pattern, string, timeout=None):
        captured["timeout"] = timeout
        return []

    monkeypatch.setattr(text_mod.regex, "findall", fake_findall)

    # TokenSearcher.findall resolves the module constant at call time.
    monkeypatch.setattr(text_mod, "TOKENSEARCH_TIMEOUT", 12.5)
    text_mod.TokenSearcher(["a", "b"]).findall("<a>")
    assert captured["timeout"] == 12.5

    monkeypatch.setattr(text_mod, "TOKENSEARCH_TIMEOUT", None)
    text_mod.TokenSearcher(["a", "b"]).findall("<a>")
    assert captured["timeout"] is None

    # Text.findall resolves it the same way.
    monkeypatch.setattr(text_mod, "TOKENSEARCH_TIMEOUT", 7.0)
    text_mod.Text(["a", "b"]).findall("<a>")
    assert captured["timeout"] == 7.0

    # An explicit timeout= still overrides the module default.
    text_mod.TokenSearcher(["a", "b"]).findall("<a>", timeout=3)
    assert captured["timeout"] == 3


def test_findall_timeout_bounds_catastrophic_query():
    """A quantified query that backtracks is abandoned at the timeout."""
    ts = TokenSearcher(["a"] * 20000)  # long run of 'a', no 'b'
    with pytest.raises(TimeoutError):
        ts.findall("<a>+<b>", timeout=1)


def _star_query_worker(n):
    """Run the benign-looking ``<a>*<b>`` over a long run of 'a'; exit 0/3."""
    try:
        TokenSearcher(["a"] * n).findall("<a>*<b>")
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        os._exit(3)


def test_findall_star_query_is_linear():
    """``<a>*<b>`` over a long token run must finish quickly, not scan O(n^2).

    Run in a spawned process with a hard deadline: the ``regex`` scan returns in
    milliseconds, while the previous stdlib-``re`` version is quadratic and needs
    minutes at this size, so a regression is terminated instead of hanging the
    suite.
    """
    n = 200_000
    deadline = 30
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_star_query_worker, args=(n,))
    proc.start()
    proc.join(deadline)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "TokenSearcher.findall did not finish in time: quadratic scan regressed"
        )
    assert proc.exitcode == 0, f"worker failed (exit {proc.exitcode})"
