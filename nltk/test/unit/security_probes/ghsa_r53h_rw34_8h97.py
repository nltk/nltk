"""GHSA-r53h-rw34-8h97 [moderate] : Algorithmic DoS (CWE-407) from front-of-sequence
mutation (list.pop(0) / reslice) in a loop, giving quadratic time on wide input.

The fix routes the right-factoring loop of ``chomsky_normal_form`` through a
``deque`` and ``popleft`` (O(1) front consume) instead of ``nodeCopy.pop(0)`` on
a list (O(n) front removal, O(n**2) over the whole loop).
"""

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, scaling_ratio


@probe("GHSA-r53h-rw34-8h97")
def _chomsky_front_pop_quadratic():
    """Drive chomsky_normal_form on a flat tree of n children and measure scaling.

    A fresh tree is built per call because the transform mutates in place. The
    fixed sink consumes children from the front in O(1), so wall time scales
    ~linearly (about 4x for 4x input); a reintroduced O(n) front pop would scale
    super-linearly and trip the quadratic ratio.
    """
    from nltk.tree import Tree
    from nltk.tree.transforms import chomsky_normal_form

    def op(n):
        chomsky_normal_form(Tree("S", ["w%d" % i for i in range(n)]))

    small, big = 2000, 8000  # big == 4 * small
    ratio = scaling_ratio(op, small, big)
    detail = "chomsky_normal_form scales %.1fx over 4x input (%d->%d children)" % (
        ratio,
        small,
        big,
    )
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "quadratic front-of-sequence mutation: " + detail
    return FIXED, "linear front consume: " + detail
