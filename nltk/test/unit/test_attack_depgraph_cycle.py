# Natural Language Toolkit: DependencyGraph cycle-detection regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Regression tests for the dead cycle guard in DependencyGraph (CWE-407 guard).

`contains_cycle` was rewritten to an iterative walk to replace an O(V^3)+
transitive-closure blowup (a CPU DoS on large graphs). The rewrite iterated
`node["deps"]` directly. `_parse` and `add_arc` store `deps` as a
relation->[addresses] mapping, so bare iteration yields relation-label keys, not
addresses: every edge was skipped and `contains_cycle` returned `False` on every
graph parsed from CoNLL / Malt-TAB data, silently disabling the guard and the
cycle-collapse branch of NonprojectiveDependencyParser that depends on it. The
same bug sat in `get_cycle_path`. Both now flatten the mapping through
`_dep_addresses`, which also accepts the legacy list-of-addresses form.

The real-data half checks every Penn dependency_treebank graph against an
independent reference check (Kahn 1962, cited at
``_topological_sort_finds_cycle``), plants cycles in real sentences, fuzzes
random CoNLL graphs, and runs the ProbabilisticNonprojectiveParser, whose MST
step is the in-tree consumer of `contains_cycle`: with the dead guard its own
demo parse was a cyclic, rootless graph, which its doctest never looked at.
"""

import random
import warnings
from collections import defaultdict, deque
from itertools import pairwise

import pytest

from nltk.parse.dependencygraph import DependencyGraph


def _acyclic_chain(n):
    rows = ["w1\tX\t0\tROOT"] + [f"w{i}\tX\t{i - 1}\tdep" for i in range(2, n + 1)]
    return "\n".join(rows) + "\n"


def test_contains_cycle_detects_a_cycle_in_a_parsed_graph():
    """A real 1<->2 cycle parsed from CoNLL is detected.

    Teeth: before the fix, bare iteration of the dict-shaped deps yielded
    relation labels, so this returned False and the guard was dead.
    """
    graph = DependencyGraph("w1\tX\t2\tdep\nw2\tX\t1\tdep\n")
    result = graph.contains_cycle()
    assert result, "contains_cycle must report the parsed cycle, not False"
    assert set(result) == {1, 2}


def test_contains_cycle_false_on_a_parsed_acyclic_chain():
    """An acyclic parsed chain is a true negative (no spurious cycle)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph = DependencyGraph(_acyclic_chain(8))
    assert graph.contains_cycle() is False


def test_contains_cycle_still_handles_the_legacy_list_deps_form():
    """The hand-built list-of-addresses form (the module doctest) is unchanged."""
    graph = DependencyGraph()
    graph.nodes = {
        0: {"word": None, "deps": [1], "rel": "TOP", "address": 0},
        1: {"word": None, "deps": [2], "rel": "N", "address": 1},
        2: {"word": None, "deps": [4], "rel": "N", "address": 2},
        3: {"word": None, "deps": [1], "rel": "N", "address": 3},
        4: {"word": None, "deps": [3], "rel": "N", "address": 4},
    }
    graph.root = graph.nodes[0]
    assert graph.contains_cycle() == [1, 2, 4, 3]


def test_get_cycle_path_follows_parsed_dict_deps():
    """get_cycle_path walks the parsed mapping too (it shared the dead-guard bug).

    A self-loop at node 1 (`w1` headed by itself) gives get_cycle_path an edge
    to follow; before the fix it iterated relation labels and found none.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph = DependencyGraph("w1\tX\t1\tdep\n")
    path = graph.get_cycle_path(graph.get_by_address(1), 1)
    assert path == [1]


def _edges(graph):
    """Edges head->dependent as the walk reads them from each node's deps."""
    edges = set()
    for address, node in graph.nodes.items():
        deps = node["deps"]
        targets = (
            [t for group in deps.values() for t in group]
            if isinstance(deps, dict)
            else list(deps)
        )
        edges.update((address, target) for target in targets)
    return edges


def _head_edges(graph):
    """Edges from each node's own head field, independent of deps."""
    return {
        (node["head"], address)
        for address, node in graph.nodes.items()
        if address is not None and node.get("head") is not None
    }


def _topological_sort_finds_cycle(graph, edges):
    """Reference cycle check: Kahn's topological sort leaves a node unvisited
    iff the graph has a directed cycle.

    A. B. Kahn. 1962. Topological sorting of large networks. Communications of
    the ACM 5(11):558-562. https://doi.org/10.1145/368996.369025

    "Oracle" in this file means a trusted reference answer for a test (the
    software-testing sense), not the parsing oracle that tells a transition
    parser its next action (Nivre, Kuhlmann and Hall 2009, IWPT, W09-3811).
    It reads edges from each node's own head field, never from ``deps``, so a
    bug in the walk under test cannot hide a bug here.
    """
    nodes = [a for a in graph.nodes if a is not None]
    indegree = dict.fromkeys(nodes, 0)
    out = defaultdict(list)
    for head, dep in edges:
        if head in indegree and dep in indegree:
            out[head].append(dep)
            indegree[dep] += 1
    queue = deque(n for n in nodes if indegree[n] == 0)
    seen = 0
    while queue:
        node = queue.popleft()
        seen += 1
        for dep in out[node]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)
    return seen != len(nodes)


def _is_cycle(graph, path):
    ring = list(path) + [path[0]]
    edges = _edges(graph)
    return all(edge in edges for edge in pairwise(ring))


def _rewired_conll(graph, new_heads):
    rows = []
    for address in sorted(a for a in graph.nodes if a):
        node = graph.nodes[address]
        head = new_heads.get(address, node["head"])
        rows.append(f"{node['word']}\t{node['tag']}\t{head}\t{node['rel']}")
    return "\n".join(rows) + "\n"


@pytest.fixture(scope="module")
def treebank_graphs():
    from nltk.corpus import dependency_treebank

    try:
        return dependency_treebank.parsed_sents()
    except LookupError:
        pytest.skip("dependency_treebank is not installed")


def test_every_real_treebank_graph_is_acyclic_and_every_head_edge_is_walked(
    treebank_graphs,
):
    """All 3914 Penn dependency_treebank graphs: contains_cycle() is False, the
    topological-sort reference check on the head fields agrees, and the edges
    the walk reads from deps are exactly the head edges (the guard sees real
    edges)."""
    assert len(treebank_graphs) > 3000
    for graph in treebank_graphs:
        head_edges = _head_edges(graph)
        assert _edges(graph) == head_edges
        assert not _topological_sort_finds_cycle(graph, head_edges)
        assert graph.contains_cycle() is False


def test_cycle_planted_in_real_sentences_is_found_with_a_real_cycle_path(
    treebank_graphs,
):
    """Rewire one head in each of 200 real sentences to a descendant of that
    node, reparse the CoNLL text and require a reported path made of real
    edges. Teeth: develop returned False on every one of these."""
    rng = random.Random(20261016)
    planted = 0
    for graph in treebank_graphs[:400]:
        children = defaultdict(list)
        for address in (a for a in graph.nodes if a):
            children[graph.nodes[address]["head"]].append(address)
        parents = [a for a in graph.nodes if a and children[a]]
        if not parents:
            continue
        node = rng.choice(parents)
        leaf = node
        while children[leaf]:
            leaf = rng.choice(children[leaf])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rewired = DependencyGraph(
                _rewired_conll(graph, {node: leaf}), top_relation_label="ROOT"
            )
        assert _topological_sort_finds_cycle(rewired, _head_edges(rewired))
        path = rewired.contains_cycle()
        assert path and _is_cycle(rewired, path), (node, leaf, path)
        planted += 1
        if planted == 200:
            break
    assert planted == 200


def test_random_graphs_agree_with_an_independent_cycle_oracle():
    """1000 seeded random CoNLL graphs (1 to 12 words, heads drawn freely, so
    self-loops, several cycles and rootless graphs occur): contains_cycle()
    truthiness equals the topological-sort verdict and every reported path is
    a real cycle."""
    rng = random.Random(1016)
    cyclic = 0
    for _ in range(1000):
        size = rng.randint(1, 12)
        rows = [f"w{a}\tNN\t{rng.randint(0, size)}\tdep" for a in range(1, size + 1)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            graph = DependencyGraph("\n".join(rows) + "\n", top_relation_label="ROOT")
        expected = _topological_sort_finds_cycle(graph, _head_edges(graph))
        path = graph.contains_cycle()
        assert bool(path) == expected
        if path:
            cyclic += 1
            assert _is_cycle(graph, path)
    assert cyclic > 500


def test_probabilistic_nonprojective_parser_collapses_the_cycle_in_its_demo():
    """The parser's demo scorer makes 2->1 and 1->2 the best incoming arcs, a
    cycle the maximum-spanning-tree step must collapse. With the dead guard the
    parse was the cyclic, rootless graph {1->2, 2->1, 2->3}; it is the rooted
    spanning tree 0->1->2->3. The module doctest only checks len(parses).

    The parser follows McDonald, Pereira, Ribarov and Hajic. 2005. Non-projective
    dependency parsing using spanning tree algorithms. HLT/EMNLP, pages 523-530,
    H05-1066, whose cycle contraction is the Chu-Liu/Edmonds algorithm:
    Y. J. Chu and T. H. Liu. 1965. On the shortest arborescence of a directed
    graph. Scientia Sinica 14:1396-1400; J. Edmonds. 1967. Optimum branchings.
    Journal of Research of the National Bureau of Standards 71B(4):233-240.
    """
    from nltk.parse.nonprojectivedependencyparser import (
        DemoScorer,
        ProbabilisticNonprojectiveParser,
    )

    parser = ProbabilisticNonprojectiveParser()
    parser.train([], DemoScorer())
    parses = list(parser.parse(["v1", "v2", "v3"], [None, None, None]))
    assert len(parses) == 1
    assert _edges(parses[0]) == {(0, 1), (1, 2), (2, 3)}
    assert parses[0].contains_cycle() is False
