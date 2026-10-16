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
"""

import warnings

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
