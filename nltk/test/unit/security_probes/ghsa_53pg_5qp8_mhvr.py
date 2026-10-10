"""GHSA-53pg-5qp8-mhvr [draft] : Uncontrolled recursion (CWE-674) in the WordNet
``Synset`` hypernym walkers ``max_depth``, ``min_depth``, ``hypernym_paths`` and
``hypernym_distances``. They recursed through other synsets with no visited
set, so a cyclic or over-deep hypernym graph in crafted corpus data recursed
until ``RecursionError``.

The fix threads a per-path visited set and a depth cap through the four
walkers and refuses a cycle or an over-deep chain with a clear ValueError.
"""

from ._base import FIXED, VULNERABLE, probe

WALKERS = ("max_depth", "min_depth", "hypernym_paths", "hypernym_distances")


def _node_class():
    """A synthetic Synset exposing only the hypernym accessor the walkers use
    (``_broader``), so the graph shape is under the probe's control and no
    corpus is needed."""
    from nltk.corpus.reader.wordnet import Synset

    class Node(Synset):
        def __init__(self, name, up):
            self._name = name
            self._up = up

        def _broader(self):
            return self._up

        def hypernyms(self):
            return self._up

        def instance_hypernyms(self):
            return []

        def _hypernyms(self):
            return self._up

        def _instance_hypernyms(self):
            return []

    return Node


def _chain(Node, length):
    node = Node("root", [])
    for i in range(length):
        node = Node("n%d" % i, [node])
    return node


@probe("GHSA-53pg-5qp8-mhvr")
def _hypernym_walkers_cycle_and_depth():
    Node = _node_class()
    problems = []
    for walker in WALKERS:
        a = Node("a", [])
        b = Node("b", [a])
        a._up = [b]  # a <-> b cycle
        try:
            getattr(a, walker)()
        except ValueError as exc:
            if "cycle" not in str(exc):
                problems.append(f"{walker}: cycle rejected without the guard: {exc}")
        except RecursionError:
            problems.append("%s: cycle recursed to RecursionError" % walker)
        else:
            problems.append("%s: cycle walked to completion" % walker)
        try:
            getattr(_chain(Node, 2000), walker)()
        except ValueError as exc:
            if "_MAX_HYPERNYM_DEPTH" not in str(exc):
                problems.append(f"{walker}: chain rejected without the guard: {exc}")
        except RecursionError:
            problems.append("%s: 2000-deep chain recursed to RecursionError" % walker)
        else:
            problems.append("%s: 2000-deep chain walked with no depth bound" % walker)
    if problems:
        return VULNERABLE, "; ".join(problems)[:300]
    return (
        FIXED,
        "all four walkers refuse a cycle and a 2000-deep chain with ValueError",
    )
