# Natural Language Toolkit: tests for picklesec.harden_object_graph
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The bounded, cycle-safe post-unpickle state walk.
An allowlist gates WHICH classes are built, not the STATE they are handed; this
walk lets a visitor neutralise that state without recursing, looping or unbounded."""

import pickle

import pytest

from nltk.picklesec import harden_object_graph


class Node:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _collector(seen):
    def visit(obj):
        seen.append(obj)
        return False

    return visit


def test_returns_the_root_unchanged():
    root = Node()
    assert harden_object_graph(root, lambda o: False) is root


def test_visits_nested_object_attributes():
    seen = []
    a = Node(x=1)
    a.child = Node(y=2)
    harden_object_graph(a, _collector(seen))
    assert a in seen and a.child in seen and 1 in seen and 2 in seen


def test_descends_dict_keys_and_values():
    seen = []
    harden_object_graph({"k": "v"}, _collector(seen))
    assert "k" in seen and "v" in seen


@pytest.mark.parametrize("container", [[1, 2], (1, 2), {1, 2}, frozenset({1, 2})])
def test_descends_every_sequence_kind(container):
    seen = []
    harden_object_graph(container, _collector(seen))
    assert 1 in seen and 2 in seen


def test_cycle_terminates_and_visits_each_node_once():
    a, b = Node(), Node()
    a.b = b
    b.a = a  # cycle
    seen = []
    harden_object_graph(a, _collector(seen))
    assert seen.count(a) == 1 and seen.count(b) == 1


def test_truthy_visit_stops_descent_into_that_node():
    inner = Node(secret="unreached")
    root = Node(inner=inner)
    seen = []

    def visit(obj):
        seen.append(obj)
        return obj is root  # claim root, do not descend into inner

    harden_object_graph(root, visit)
    assert root in seen and inner not in seen


def test_node_cap_raises_unpickling_error():
    root = [Node() for _ in range(10)]
    with pytest.raises(pickle.UnpicklingError):
        harden_object_graph(root, lambda o: False, max_nodes=3)


def test_visitor_neutralises_state_on_every_matching_node():
    leaves = [Node(timeout=None) for _ in range(5)]
    root = Node(children=leaves)

    def visit(obj):
        if isinstance(obj, Node) and getattr(obj, "timeout", "keep") is None:
            obj.timeout = "CAPPED"
        return False

    harden_object_graph(root, visit)
    assert all(leaf.timeout == "CAPPED" for leaf in leaves)
