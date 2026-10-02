"""GHSA-ff5c-cp5c-9wjf [medium] -- Uncontrolled resource consumption in RecursiveDescentParser via ambiguous or left-recursive grammars"""

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-ff5c-cp5c-9wjf")
def _recursivedescent_unbounded():
    """RecursiveDescentParser enumerated parses with no bound."""
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser

    # A left-recursive 'S -> S S' blows the stack (RecursionError) before max_time is
    # consulted; this right-branching ambiguous form stresses wall-clock so the fix runs.
    grammar = CFG.fromstring("S -> 'a' S S | 'a'")
    try:
        seconds = timed(lambda: list(RecursiveDescentParser(grammar).parse(["a"] * 18)))
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "ambiguous grammar ran %.1fs" % seconds
    return FIXED, "ambiguous grammar completed in %.2fs" % seconds
