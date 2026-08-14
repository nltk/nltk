"""GHSA-ff5c-cp5c-9wjf [medium] -- Uncontrolled resource consumption in RecursiveDescentParser via ambiguous or left-recurs"""
from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-ff5c-cp5c-9wjf")
def _recursivedescent_unbounded():
    """RecursiveDescentParser enumerated parses with no bound."""
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser

    grammar = CFG.fromstring("S -> S S | 'a'")
    try:
        seconds = timed(lambda: list(RecursiveDescentParser(grammar).parse(["a"] * 12)))
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "ambiguous grammar ran %.1fs" % seconds
    return FIXED, "ambiguous grammar completed in %.2fs" % seconds
