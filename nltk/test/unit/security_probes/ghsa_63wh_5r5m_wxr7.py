"""GHSA-63wh-5r5m-wxr7 [medium] -- Uncontrolled recursion in Tree.fromlist causes denial of service via deeply nested list input (CWE-674)"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-63wh-5r5m-wxr7")
def _tree_fromlist_recursion():
    """Convert a deeply nested list with ``Tree.fromlist``.

    ``fromstring`` bounds bracket depth with ``MAX_TREE_DEPTH``, but ``fromlist``
    recursed once per level with no bound, so a crafted nested list crashed with
    an uncaught ``RecursionError`` (a DoS). It must now reject the input with a
    bounded ``ValueError`` before reaching that depth.
    """
    from nltk.tree import Tree
    from nltk.tree.tree import MAX_TREE_DEPTH

    payload = "leaf"
    for _ in range(MAX_TREE_DEPTH + 200):
        payload = ["N", payload]
    try:
        Tree.fromlist(payload)
    except RecursionError:
        return VULNERABLE, "Tree.fromlist recursed to RecursionError (uncontrolled)"
    except ValueError as exc:
        return FIXED, "deep nested list rejected: %s" % str(exc)[:56]
    return VULNERABLE, "Tree.fromlist accepted an adversarially deep list"
