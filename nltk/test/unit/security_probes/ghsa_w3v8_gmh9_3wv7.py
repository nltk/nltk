"""GHSA-w3v8-gmh9-3wv7 [medium] -- ReDoS in nltk.tgrep via unvalidated user-supplied regular expressions"""

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-w3v8-gmh9-3wv7")
def _tgrep_redos():
    """tgrep passed user regexes to re with no timeout or validation."""
    from nltk import tgrep
    from nltk.tree import Tree

    # Compiling is fast either way; the catastrophic backtracking only fires when
    # the predicate MATCHES a hostile node label, so drive the match.
    try:
        predicate = tgrep.tgrep_compile("/([ab]|[ab])*$/")
        hostile = Tree("ab" * 25 + "!", ["x"])
        seconds = timed(lambda: predicate(hostile))
    except Exception as exc:
        return FIXED, "hostile pattern rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "tgrep match took %.1fs" % seconds
    return FIXED, "hostile pattern matched in %.3fs" % seconds
