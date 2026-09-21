"""GHSA-89p3-fcch-88ph [moderate]: quadratic (O(n**2)) tail-reslicing in the
CCG lexicon parser lets a long flat application chain cause denial of service
(CWE-407).
"""

from ._base import (
    FIXED,
    QUADRATIC_RATIO,
    VULNERABLE,
    probe,
    scaling_ratio,
)


@probe("GHSA-89p3-fcch-88ph")
def _ccg_lexicon_quadratic_parse():
    """Parse a long flat ``S/S/S/.../S`` chain and confirm the parse stays linear.

    Pre-fix, matchBrackets/nextCategory/augParseCategory resliced the remaining
    tail (and NEXTPRIM_RE/APP_RE captured it with a trailing ``(.*)``) on every
    step, so parsing a chain of length n copied O(n) characters n times: O(n**2).
    The fix threads an integer cursor instead, so the scaling factor for a 4x
    longer input stays near linear. VULNERABLE if it is super-linear.
    """
    from nltk.ccg import lexicon
    from nltk.ccg.lexicon import MAX_PARSE_LEN, fromstring

    def lex(n):
        return ":- S\nw => S" + "/S" * n + "\n"

    def op(n):
        return fromstring(lex(n))

    small, big = 10000, 40000
    ratio = scaling_ratio(op, small, big)
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "parse time scales %.1fx for 4x input (quadratic)" % ratio

    # Defense in depth: a category longer than MAX_PARSE_LEN must be rejected
    # rather than parsed, so an over-cap chain cannot be walked at all.
    over = ":- S\nw => S" + "/S" * (MAX_PARSE_LEN // 2 + 10) + "\n"
    try:
        fromstring(over)
    except ValueError as exc:
        if "MAX_PARSE_LEN" not in str(exc):
            return VULNERABLE, "over-cap input rejected but not by the length cap"
        capped = True
    else:
        return VULNERABLE, "category longer than MAX_PARSE_LEN was parsed, not capped"

    assert lexicon.MAX_PARSE_LEN == MAX_PARSE_LEN and capped
    return (
        FIXED,
        "scaling %.1fx (linear); over-cap chain rejected by MAX_PARSE_LEN" % ratio,
    )
