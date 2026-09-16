"""GHSA-63wh-5r5m-wxr7 [moderate] -- Uncontrolled recursion in
Tree.fromlist causes denial of service via deeply nested list input.
"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-63wh-5r5m-wxr7")
def _tree_fromlist_recursion():
    """Uncontrolled recursion in Tree.fromlist causes a crash."""
    from nltk.tree import Tree

    n = 5000
    # Build ["S", ["S", ["S", ...]]] n levels deep.
    nested = []
    current = nested
    for _ in range(n):
        child = []
        current.append("S")
        current.append(child)
        current = child

    try:
        Tree.fromlist(nested)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped from Tree.fromlist()"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deeply nested list converted without crashing"
