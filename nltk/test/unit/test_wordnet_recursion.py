import sys

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


def test_long_chain_is_refused_not_truncated():
    nodes = [MockNode(str(i)) for i in range(1500)]
    for i in range(1499):
        nodes[i]._children = [nodes[i + 1]]
    # No RecursionError, and no tree silently cut at MAX_RECURSION_DEPTH either.
    with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH"):
        acyclic_depth_first(nodes[0], lambda x: x.rel(), depth=-1)


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
    with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH"):
        acyclic_branches_depth_first(nodes[0], lambda x: x.rel(), depth=-1)


def test_dic2tree_short_chain():
    d = {}
    for i in range(5):
        d[str(i)] = [str(i + 1)] if i < 4 else []
    result = acyclic_dic2tree("0", d)
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]
    assert depth == 4


def test_dic2tree_long_chain_refused():
    d = {}
    for i in range(1500):
        d[str(i)] = [str(i + 1)] if i < 1499 else []
    with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH"):
        acyclic_dic2tree("0", d)


def test_dic2tree_explicit_depth():
    d = {}
    for i in range(10):
        d[str(i)] = [str(i + 1)] if i < 9 else []
    result = acyclic_dic2tree("0", d, depth=20)
    depth = 0
    current = result
    while isinstance(current, list) and len(current) > 1:
        depth += 1
        current = current[1]
    assert depth == 9


def test_dic2tree_negative_depth():
    d = {"a": ["b"]}
    with pytest.raises(ValueError, match="depth must be >= -1"):
        acyclic_dic2tree("a", d, depth=-2)


def test_dic2tree_cycle():
    # Simple cycle: a -> b -> a
    d = {"a": ["b"], "b": ["a"]}
    result = acyclic_dic2tree("a", d, verbose=False)
    # Should return ['a', ['b']] because the cycle is truncated
    assert result == ["a", ["b"]]


# The bound on every recursive relation walk (GHSA-8846-p9w9-5frf): a walk
# deeper than MAX_RECURSION_DEPTH is refused with ValueError whatever depth was
# asked for; a walk at the bound, or one a smaller depth truncates, is returned.

DEEP = 3000
#: nltk.util itself: ``import nltk.util`` binds the nltk.stem.util that the
#: package's star imports leave on the ``nltk.util`` attribute.
UTIL = sys.modules[acyclic_depth_first.__module__]


def _chain_root(n):
    """The root of an n node chain, as nodes whose children come from ``rel``."""
    nodes = [MockNode(str(i)) for i in range(n)]
    for parent, child in zip(nodes, nodes[1:]):
        parent._children = [child]
    return nodes[0]


def _chain_dict(n):
    return {str(i): [str(i + 1)] if i < n - 1 else [] for i in range(n)}


WALKS = {
    "acyclic_depth_first": lambda n, depth: acyclic_depth_first(
        _chain_root(n), lambda x: x.rel(), depth
    ),
    "acyclic_branches_depth_first": lambda n, depth: acyclic_branches_depth_first(
        _chain_root(n), lambda x: x.rel(), depth
    ),
    "acyclic_dic2tree": lambda n, depth: acyclic_dic2tree("0", _chain_dict(n), depth),
}


@pytest.mark.parametrize("name", sorted(WALKS))
@pytest.mark.parametrize("n", [MAX_RECURSION_DEPTH + 2, DEEP])
def test_unbounded_walk_deeper_than_the_bound_is_refused(name, n):
    with pytest.raises(ValueError, match=r"MAX_RECURSION_DEPTH \(500\)") as caught:
        WALKS[name](n, -1)
    assert not isinstance(caught.value, RecursionError)


@pytest.mark.parametrize("name", sorted(WALKS))
@pytest.mark.parametrize("depth", [MAX_RECURSION_DEPTH + 1, 2000, DEEP * 10])
def test_explicit_depth_over_the_bound_is_refused_not_a_recursion_error(name, depth):
    with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH") as caught:
        WALKS[name](DEEP, depth)
    assert not isinstance(caught.value, RecursionError)


@pytest.mark.parametrize("name", sorted(WALKS))
def test_refusal_holds_with_a_raised_recursion_limit(name):
    saved = sys.getrecursionlimit()
    sys.setrecursionlimit(DEEP * 10)
    try:
        with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH"):
            WALKS[name](DEEP, -1)
    finally:
        sys.setrecursionlimit(saved)


@pytest.mark.parametrize("name", sorted(WALKS))
@pytest.mark.parametrize("depth", [-1, MAX_RECURSION_DEPTH, 2000])
def test_walk_at_the_bound_is_returned_in_full(name, depth):
    # n nodes nest n - 1 levels below the root: the deepest sits at the bound.
    tree = WALKS[name](MAX_RECURSION_DEPTH + 1, depth)
    assert traversal_depth(tree) == MAX_RECURSION_DEPTH


@pytest.mark.parametrize("name", sorted(WALKS))
@pytest.mark.parametrize("depth", [0, 1, 400, MAX_RECURSION_DEPTH])
def test_requested_depth_truncates_a_deep_walk(name, depth):
    assert traversal_depth(WALKS[name](DEEP, depth)) == depth


@pytest.mark.parametrize("name", sorted(WALKS))
def test_raising_the_module_bound_allows_a_deeper_walk(name, monkeypatch):
    with pytest.raises(ValueError, match=r"sys.modules\['nltk.util'\]"):
        WALKS[name](700, -1)
    monkeypatch.setattr(UTIL, "MAX_RECURSION_DEPTH", 700)
    assert traversal_depth(WALKS[name](700, -1)) == 699


@pytest.mark.parametrize("name", sorted(WALKS))
def test_teeth_the_deep_walk_overflows_without_the_bound(name, monkeypatch):
    assert sys.getrecursionlimit() < DEEP
    monkeypatch.setattr(UTIL, "MAX_RECURSION_DEPTH", sys.maxsize)
    with pytest.raises(RecursionError):
        WALKS[name](DEEP, -1)


def test_unbounded_cycle_marks_count_down_from_minus_one():
    # c -> a closes a cycle two levels below the root: remaining depth -1 - 2 - 1.
    a, b, c = MockNode("a"), MockNode("b"), MockNode("c")
    a._children, b._children, c._children = [b], [c], [a]
    tree = acyclic_branches_depth_first(a, lambda x: x.rel(), cut_mark="...")
    assert tree[1][1][1] == f"Cycle({a},-4,...)"


# The public WordNet entry points, on the real corpus.


def _wordnet():
    from nltk.corpus import wordnet as wn

    try:
        wn.ensure_loaded()
    except LookupError:
        pytest.skip("the WordNet corpus is not installed")
    return wn


def _flatten(tree):
    stack, seen = [tree], []
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        else:
            seen.append(node)
    return seen


def test_real_wordnet_full_hyponym_walks_are_not_truncated():
    wn = _wordnet()
    entity = wn.synset("entity.n.01")
    hypo = lambda s: sorted(s.hyponyms())
    reachable = {entity, *entity.closure(hypo)}
    assert len(reachable) > 70000
    assert set(_flatten(entity.acyclic_tree(hypo))) == reachable
    assert set(_flatten(entity.mst(hypo))) == reachable
    assert set(_flatten(entity.tree(hypo, depth=3))) < reachable


def test_real_wordnet_deep_custom_relation_is_refused_through_synset_methods():
    # The advisory's shape: a genuinely acyclic relation chain longer than the bound.
    wn = _wordnet()
    dog = wn.synset("dog.n.01")
    rel = lambda x: [x + 1] if isinstance(x, int) else [0]
    rel_to = lambda n: lambda x: [] if x == n else rel(x)
    for method in (dog.tree, dog.acyclic_tree, dog.mst):
        with pytest.raises(ValueError, match="MAX_RECURSION_DEPTH"):
            method(rel_to(DEEP))
    # dog, then 0 .. MAX_RECURSION_DEPTH - 1: the deepest sits at the bound.
    assert traversal_depth(dog.tree(rel_to(MAX_RECURSION_DEPTH - 1))) == (
        MAX_RECURSION_DEPTH
    )
    assert traversal_depth(dog.tree(rel_to(DEEP), depth=10)) == 10
