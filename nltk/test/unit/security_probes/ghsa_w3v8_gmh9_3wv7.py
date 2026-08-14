"""GHSA-w3v8-gmh9-3wv7 [medium] -- ReDoS in nltk.tgrep via unvalidated user-supplied regular expressions

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-w3v8-gmh9-3wv7")
def _tgrep_redos():
    """tgrep passed user regexes to re with no timeout or validation."""
    from nltk import tgrep

    try:
        seconds = timed(tgrep.tgrep_compile, '/([ab]|[ab])*$/')
    except Exception as exc:
        return FIXED, "hostile pattern rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "tgrep compile took %.1fs" % seconds
    return FIXED, "hostile pattern handled in %.3fs" % seconds
