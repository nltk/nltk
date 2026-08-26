import pytest

from nltk.util import (
    MAX_RECURSION_DEPTH,
    acyclic_branches_depth_first,
    acyclic_depth_first,
    acyclic_dic2tree,
)


class MockNode:
    def __init__(self, name, children=None):
        self.name = name
        self._children = children or []

    def rel(self):
        return self._children


def traversal_depth(result):
    """Iteratively compute the depth of the nested list structure."""
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]  # go to the child subtree
    return depth


def test_short_chain():
    a = MockNode("a", [MockNode("b")])
    result = list(acyclic_depth_first(a, lambda x: x.rel(), depth=5))
    assert len(result) == 2  # [a, [b]]
    assert traversal_depth(result) == 1


def test_long_chain_does_not_crash_and_respects_cap():
    nodes = [MockNode(str(i)) for i in range(1500)]
    for i in range(1499):
        nodes[i]._children = [nodes[i + 1]]
    result = list(acyclic_depth_first(nodes[0], lambda x: x.rel(), depth=-1))
    # Ensure no RecursionError (vulnerability fixed)
    # Also verify depth is capped at MAX_RECURSION_DEPTH
    depth = traversal_depth(result)
    assert depth <= MAX_RECURSION_DEPTH


def test_user_can_pass_explicit_depth():
    nodes = [MockNode(str(i)) for i in range(10)]
    for i in range(9):
        nodes[i]._children = [nodes[i + 1]]
    result = list(acyclic_depth_first(nodes[0], lambda x: x.rel(), depth=2000))
    # Explicit depth should traverse all 10 nodes, not capped.
    depth = traversal_depth(result)
    assert depth == 9  # root + 9 children = 10 nodes


def test_negative_depth_raises_value_error():
    nodes = [MockNode("a")]
    with pytest.raises(ValueError, match="depth must be >= -1"):
        list(acyclic_depth_first(nodes[0], lambda x: x.rel(), depth=-2))
    # Also verify for branches
    with pytest.raises(ValueError, match="depth must be >= -1"):
        list(acyclic_branches_depth_first(nodes[0], lambda x: x.rel(), depth=-2))


def test_branches_same_behavior():
    a = MockNode("a", [MockNode("b")])
    result = list(acyclic_branches_depth_first(a, lambda x: x.rel(), depth=2))
    assert len(result) == 2
    assert isinstance(result[1], list)
    assert result[1][0].name == "b"

    nodes = [MockNode(str(i)) for i in range(1500)]
    for i in range(1499):
        nodes[i]._children = [nodes[i + 1]]
    result = list(acyclic_branches_depth_first(nodes[0], lambda x: x.rel(), depth=-1))
    depth = traversal_depth(result)
    assert depth <= MAX_RECURSION_DEPTH

def test_dic2tree_short_chain():
    d = {}
    for i in range(5):
        d[str(i)] = [str(i+1)] if i < 4 else []
    result = acyclic_dic2tree('0', d)
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]
    assert depth == 4

def test_dic2tree_long_chain_capped():
    d = {}
    for i in range(1500):
        d[str(i)] = [str(i+1)] if i < 1499 else []
    result = acyclic_dic2tree('0', d)
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]
    assert depth <= MAX_RECURSION_DEPTH

def test_dic2tree_explicit_depth():
    d = {}
    for i in range(10):
        d[str(i)] = [str(i+1)] if i < 9 else []
    result = acyclic_dic2tree('0', d, depth=20)
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]
    assert depth == 9

def test_dic2tree_negative_depth():
    d = {'a': ['b']}
    with pytest.raises(ValueError, match="depth must be >= -1"):
        acyclic_dic2tree('a', d, depth=-2)

def test_dic2tree_cycle():
    # Simple cycle: a -> b -> a
    d = {'a': ['b'], 'b': ['a']}
    result = acyclic_dic2tree('a', d, verbose=False)
    # Should return ['a', ['b']] because the cycle is truncated
    assert result == ['a', ['b']]
