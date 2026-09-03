"""Regression tests for the quadratic ReDoS in valuation parsing
(CWE-1333; CVE-2026-12890).

``nltk.sem.evaluate`` splits each valuation line on a ``\\s*=+>\\s*`` separator.
The greedy ``=+`` run made splitting a line that holds a long run of ``=`` not
terminated by ``>`` re-scan the run from every position, which is quadratic in
the run length -- so a single untrusted valuation string could pin a CPU core.
A ``(?<!=)`` lookbehind now lets the run be matched only at its start, making the
split linear while leaving the parse result unchanged.

The "must stay linear" test runs in a separate process with a hard timeout, and
the worker reports via its exit code (no queue/thread, so it is robust on
free-threaded builds), so a regression to the quadratic pattern cannot hang the
suite.
"""

import os

from nltk.sem import Valuation
from nltk.sem.evaluate import read_valuation

from . import _mp_ctx


def test_valuation_parsing_preserved():
    val = Valuation.fromstring(
        "noosa => n\n"
        "girl => {g1, g2}\n"
        "chase => {(b1, g1), (b2, g1)}\n"
        "x ==> y"  # multiple '=' in the separator must still work
    )
    assert val["noosa"] == "n"
    assert sorted(val["girl"]) == [("g1",), ("g2",)]
    assert sorted(val["chase"]) == [("b1", "g1"), ("b2", "g1")]
    assert val["x"] == "y"


_TIMEOUT = 20
# A line with a long run of the separator's leading character ('=') that is not
# terminated by '>'. The pre-fix greedy '=+' made splitting this quadratic (~50 s
# at this size); the fix makes it linear (~milliseconds). It is CPU-only (a ~0.5
# MB string), so there is no OOM risk.
_EVIL = "sym " + "=" * 500_000


def _parse_worker():
    try:
        # We don't care about the result/exception (the line has no valid
        # separator); only that parsing returns quickly rather than hanging.
        read_valuation(_EVIL)
    except Exception:
        pass
    os._exit(0)


def test_long_separator_run_parses_in_linear_time():
    """A long '=' run must split in linear time, not quadratic (ReDoS)."""
    ctx = _mp_ctx()
    proc = ctx.Process(target=_parse_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "valuation parsing did not finish in time -> quadratic ReDoS (CWE-1333)"
        )
    assert proc.exitcode == 0, f"worker failed (exit code {proc.exitcode})"


# Many separate long '=' runs across many lines: the per-line split must stay
# linear on each, so the whole document is linear (not quadratic per line * lines).
_EVIL_MULTILINE = "\n".join("s%d %s" % (i, "=" * 20_000) for i in range(200))


def _parse_multiline_worker():
    try:
        read_valuation(_EVIL_MULTILINE)
    except Exception:
        pass
    os._exit(0)


def test_many_separator_runs_parse_in_linear_time():
    """Many hostile '=' runs (one per line) must all stay linear."""
    ctx = _mp_ctx()
    proc = ctx.Process(target=_parse_multiline_worker)
    proc.start()
    proc.join(_TIMEOUT)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "multi-line valuation parsing did not finish in time -> quadratic ReDoS"
        )
    assert proc.exitcode == 0, f"worker failed (exit code {proc.exitcode})"


def test_valuation_split_routes_through_redos():
    """Pin the mechanism: the valuation separator split uses the bounded
    ``redos.compile`` pattern (not a raw ``re``), and the ``(?<!=)`` lookbehind
    that makes the greedy ``=+`` run fail fast is still present."""
    import inspect

    import nltk.sem.evaluate

    source = inspect.getsource(nltk.sem.evaluate)
    assert "redos.compile" in source, "valuation no longer routes through redos"
    assert "(?<!=)=+>" in source, "the fail-fast lookbehind was removed"


def test_valuation_various_separators_preserved():
    """The bounded split must not change parsing of legitimate separators."""
    val = Valuation.fromstring("a => x\nb ===> y\nc => {(p, q)}")
    assert val["a"] == "x"
    assert val["b"] == "y"
    assert sorted(val["c"]) == [("p", "q")]
