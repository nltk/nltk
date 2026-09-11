"""GHSA-3h95-x772-4765 [medium] -- Uncontrolled recursion in CCG lexicon parser causes denial of service via deeply nested category input (CWE-674)"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-3h95-x772-4765")
def _ccg_category_recursion():
    """Parse a deeply parenthesised CCG category string.

    ``matchBrackets`` (reached from ``augParseCategory`` / lexicon
    ``fromstring``) recursed once per ``(`` with no bound, so a category like
    ``(((...)))`` crashed with an uncaught ``RecursionError`` (a DoS). It must
    now reject the input with a bounded ``ValueError``.
    """
    from nltk.ccg.lexicon import MAX_CATEGORY_DEPTH, matchBrackets

    n = MAX_CATEGORY_DEPTH + 200
    payload = "(" * n + ")" * n
    try:
        matchBrackets(payload)
    except RecursionError:
        return VULNERABLE, "matchBrackets recursed to RecursionError (uncontrolled)"
    except ValueError as exc:
        return FIXED, "deeply nested category rejected: %s" % str(exc)[:50]
    return VULNERABLE, "matchBrackets accepted an adversarially deep category"
