"""GHSA-3h95-x772-4765 [moderate] -- Uncontrolled recursion in the CCG
lexicon parser causes denial of service via deeply nested category input.
"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-3h95-x772-4765")
def _ccg_lexicon_recursion():
    """Uncontrolled recursion in matchBrackets/augParseCategory causes a crash."""
    from nltk.ccg.lexicon import fromstring

    n = 2000
    lex_str = ":- S\nw => " + "(" * n + "S" + ")" * n + "\n"

    try:
        fromstring(lex_str)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped from ccg.lexicon.fromstring()"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deeply nested category parsed without crashing"
