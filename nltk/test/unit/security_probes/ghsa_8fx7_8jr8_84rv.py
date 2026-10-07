"""GHSA-8fx7-8jr8-84rv [draft] : Unbounded CPU consumption (CWE-400 / CWE-407)
in ``SteppingRecursiveDescentParser.parse``. It drives ``step()`` in a loop
that bypassed the base parser's ``max_time`` deadline, so an ambiguous or
self-embedding grammar ran without bound (24 tokens ran past 45 s).

The fix checks the deadline on every step of that loop and raises
``TimeoutError`` once ``max_time`` is exceeded.
"""

import time

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-8fx7-8jr8-84rv")
def _stepping_parser_deadline():
    """Parse 8 tokens of an exponentially ambiguous grammar under a short deadline.

    Unbounded, the stepping parse of these 8 tokens is a few seconds of work;
    the fixed loop stops it at ``max_time`` with TimeoutError.
    """
    from nltk import CFG
    from nltk.parse.recursivedescent import SteppingRecursiveDescentParser

    grammar = CFG.fromstring("S -> 'a' S | 'a' S S | 'a'")
    max_time = 0.25
    parser = SteppingRecursiveDescentParser(grammar, max_time=max_time)
    start = time.perf_counter()
    try:
        list(parser.parse(["a"] * 8))
    except TimeoutError:
        elapsed = time.perf_counter() - start
        return FIXED, "stepping parse stopped by max_time={:.2f}s after {:.2f}s".format(
            max_time,
            elapsed,
        )
    elapsed = time.perf_counter() - start
    return (
        VULNERABLE,
        "stepping parse ran {:.1f}s with max_time={:.2f}s and no TimeoutError".format(
            elapsed,
            max_time,
        ),
    )
