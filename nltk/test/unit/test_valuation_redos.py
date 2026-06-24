"""Regression tests for the quadratic ReDoS in valuation parsing
(CWE-1333; CVE-2026-12890).

``nltk.sem.evaluate`` splits each valuation line on a ``\\s*=+>\\s*`` separator.
The greedy ``=+`` run made splitting a line that holds a long run of ``=`` not
terminated by ``>`` re-scan the run from every position, which is quadratic in
the run length -- so a single untrusted valuation string could pin a CPU core.
A ``(?<!=)`` lookbehind now lets the run be matched only at its start, making the
split linear while leaving the parse result unchanged.

The "must stay linear" test runs in a spawned process with a hard timeout, and
the worker reports via its exit code (no queue/thread, so it is robust on
free-threaded builds), so a regression to the quadratic pattern cannot hang the
suite.
"""

import multiprocessing
import os

from nltk.sem import Valuation
from nltk.sem.evaluate import read_valuation


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
    ctx = multiprocessing.get_context("spawn")
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
