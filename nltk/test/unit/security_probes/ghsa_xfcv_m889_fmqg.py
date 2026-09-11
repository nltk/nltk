"""GHSA-xfcv-m889-fmqg [medium] -- Uncontrolled recursion in DependencyGraph traversal causes denial of service via deep dependency chains (CWE-674)"""

import warnings

from ._base import FIXED, VULNERABLE, probe


def _deep_conll(n):
    """A CoNLL-10 string that is one linear chain of ``n`` dependents."""
    rows = []
    for i in range(1, n + 1):
        head = i - 1
        rel = "ROOT" if i == 1 else "dep"
        rows.append(f"{i}\tw{i}\t_\tN\tN\t_\t{head}\t{rel}\t_\t_")
    return "\n".join(rows)


@probe("GHSA-xfcv-m889-fmqg")
def _dependencygraph_recursion():
    """Build a graph with a long linear dependency chain and traverse it.

    ``_tree`` / ``triples`` recursed once per dependent with no bound, so a
    crafted chain crashed with an uncaught ``RecursionError`` (a DoS). Both must
    now raise a bounded ``ValueError`` past ``MAX_GRAPH_DEPTH``.
    """
    from nltk.parse.dependencygraph import MAX_GRAPH_DEPTH, DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_deep_conll(MAX_GRAPH_DEPTH + 200))
    for label, run in (("triples", lambda: list(dg.triples())), ("_tree", dg.tree)):
        try:
            run()
        except RecursionError:
            return VULNERABLE, "%s recursed to RecursionError (uncontrolled)" % label
        except ValueError:
            continue
        return VULNERABLE, "%s accepted an adversarially deep chain" % label
    return FIXED, "deep dependency chain rejected by MAX_GRAPH_DEPTH in triples/_tree"
