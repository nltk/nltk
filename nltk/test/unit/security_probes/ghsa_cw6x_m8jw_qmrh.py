"""GHSA-cw6x-m8jw-qmrh [medium] -- Uncontrolled recursion in nltk.featstruct.FeatStructReader causes unhandled RecursionErr"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-cw6x-m8jw-qmrh")
def _featstruct_recursion():
    """Uncontrolled recursion in FeatStructReader causes a crash."""
    from nltk.featstruct import FeatStruct

    try:
        FeatStruct("[a=" * 5000 + "1" + "]" * 5000)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped to the caller"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deeply nested input parsed without crashing"
