"""GHSA-xfcv-m889-fmqg [moderate] -- Uncontrolled recursion in
DependencyGraph traversal causes denial of service via deep dependency chains.
"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-xfcv-m889-fmqg")
def _dependencygraph_recursion():
    """Uncontrolled recursion in _tree/triples causes a crash."""
    from nltk.parse.dependencygraph import DependencyGraph

    n = 5000
    # Malt-TAB: FORM TAG HEAD REL.  Token k's head is k+1; the last token
    # is the root (head 0), giving a linear chain of depth n.
    lines = []
    for i in range(1, n + 1):
        head = i + 1 if i < n else 0
        rel = "dep" if i < n else "ROOT"
        lines.append("word%d TAG %d %s" % (i, head, rel))
    conll = "\n".join(lines) + "\n"

    try:
        dg = DependencyGraph(conll)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped during graph construction"
    except Exception as exc:
        return FIXED, "bounded during construction (%s)" % type(exc).__name__

    try:
        dg.tree()
    except RecursionError:
        return VULNERABLE, "RecursionError escaped from tree()"
    except Exception as exc:
        return FIXED, "bounded in tree() (%s)" % type(exc).__name__

    try:
        list(dg.triples())
    except RecursionError:
        return VULNERABLE, "RecursionError escaped from triples()"
    except Exception as exc:
        return FIXED, "bounded in triples() (%s)" % type(exc).__name__

    return FIXED, "deeply nested dependency chain traversed without crashing"
