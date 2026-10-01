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

#: Operators in the flat chain's small and big runs: the largest 4x pair under
#: MAX_PARSE_LEN (49996 operators are 99993 characters). At 10000 the small
#: run sat under the 0.1 s floor on the macOS and Windows runners.
FLAT_SMALL = 12499
FLAT_BIG = 4 * FLAT_SMALL

#: Bracket depth of the nested leg. The pre-fix parser re-sliced the bracketed
#: text per character and did so again at every level, so the depth sets the
#: work per character; 60 lifts the fixed parser's small run off the floor.
NESTING = 60


def _nested_lexicon(chars):
    """A lexicon whose one entry is a primitive with a long subscript list,
    wrapped in NESTING brackets, ``chars`` characters of category in all."""
    inner = chars - 2 * NESTING
    subscripts = "a," * ((inner - 4) // 2) + "a"
    return (
        ":- S\nw => " + "(" * NESTING + "S[" + subscripts + "]" + ")" * NESTING + "\n"
    )


@probe("GHSA-89p3-fcch-88ph")
def _ccg_lexicon_quadratic_parse():
    """Parse the two shapes the tail re-slicing made quadratic, confirm each
    parse stays linear, then confirm an over-cap category is refused.

    Pre-fix, matchBrackets/nextCategory/augParseCategory resliced the remaining
    tail (and NEXTPRIM_RE/APP_RE captured it with a trailing ``(.*)``) on every
    step, so parsing a chain of length n copied O(n) characters n times: O(n**2).
    The fix threads an integer cursor instead, so the scaling factor for a 4x
    longer input stays near linear. VULNERABLE if either shape is super-linear.

    Both legs stay under MAX_PARSE_LEN, so the pre-fix parser's quadratic work
    is bounded by the cap and competes with its own per-step cost; measured on
    the hosted runners (nltk/nltk PR #3944), the pre-fix parser reads 11x to
    14x on the flat leg and 9x to 19x on the nested leg, the fixed parser 3.9x
    to 4.2x on both. The flat leg is the advisory's own chain and the stable
    signal; the nested leg wraps one primitive in NESTING brackets, where the
    pre-fix matchBrackets copied its tail once per character at every level,
    and covers the bracket scanner the flat leg never enters.
    """
    from nltk.ccg import lexicon
    from nltk.ccg.lexicon import MAX_PARSE_LEN, fromstring

    def lex(n):
        return ":- S\nw => S" + "/S" * n + "\n"

    def op(n):
        return fromstring(lex(n))

    ratio = scaling_ratio(op, FLAT_SMALL, FLAT_BIG, cpu_bound=True)  # computes
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "parse time scales %.1fx for 4x input (quadratic)" % ratio

    def nested(n):
        return fromstring(_nested_lexicon(n))

    nested_ratio = scaling_ratio(
        nested, MAX_PARSE_LEN // 4, MAX_PARSE_LEN, cpu_bound=True
    )
    if nested_ratio >= QUADRATIC_RATIO:
        return (
            VULNERABLE,
            "nested parse time scales %.1fx for 4x input (quadratic)" % nested_ratio,
        )

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
        "scaling %.1fx flat, %.1fx nested (linear); over-cap chain rejected by "
        "MAX_PARSE_LEN" % (ratio, nested_ratio),
    )
