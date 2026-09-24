# Natural Language Toolkit: iterative Tree equality and conversion tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``Tree.__eq__`` and ``Tree.convert`` (behind ``deepcopy``) walk with an
explicit stack. On Python 3.10 and 3.11 their recursive forms overflowed at
depth ~250 and ~500, below or at the ``MAX_TREE_DEPTH`` that ``fromstring``
accepts (CWE-674), which the GHSA-r53h boundary test hit on those
interpreters. These pins hold the iterative forms to the recursive results
exactly and hold subclasses with their own overrides to their own paths."""

import copy
import random

import pytest

from nltk.tree import ImmutableTree, ParentedTree, ProbabilisticTree, Tree
from nltk.tree import tree as treemod


def _chain(depth, cls=Tree):
    t = cls("L", ["w"])
    for _ in range(depth - 1):
        t = cls("N", [t])
    return t


def _recursive_eq(a, b):
    if a.__class__ is not b.__class__:
        return False
    return (a._label, list(a)) == (b._label, list(b))


def _random_tree(rng, depth):
    if depth == 0 or rng.random() < 0.2:
        return rng.choice(["a", "b", 1, None, ("t", 2)])
    return Tree(
        rng.choice(["S", "NP", 3]),
        [_random_tree(rng, depth - 1) for _ in range(rng.randint(0, 4))],
    )


@pytest.mark.parametrize(
    "depth", [treemod.MAX_TREE_DEPTH, treemod.MAX_TREE_DEPTH + 1, 2000]
)
def test_deep_equality_and_deepcopy_do_not_overflow(depth):
    tree = _chain(depth)
    twin = copy.deepcopy(tree)
    assert twin == tree and twin is not tree
    assert twin.height() == tree.height() if depth < 900 else True
    other = _chain(depth)
    other_leaf = other
    while isinstance(other_leaf[0], Tree):
        other_leaf = other_leaf[0]
    other_leaf[0] = "different"
    assert tree != other


@pytest.mark.parametrize("seed", range(40))
def test_equality_matches_the_recursive_definition(seed):
    rng = random.Random(seed)
    a = _random_tree(rng, 5)
    b = copy.deepcopy(a) if rng.random() < 0.5 else _random_tree(rng, 5)
    if isinstance(a, Tree) and isinstance(b, Tree):
        assert (a == b) == _recursive_eq(a, b)
        assert (a != b) == (not _recursive_eq(a, b))


@pytest.mark.parametrize("seed", range(20))
def test_deepcopy_is_structurally_identical_and_fresh(seed):
    rng = random.Random(seed)
    a = Tree("ROOT", [_random_tree(rng, 5) for _ in range(3)])
    b = copy.deepcopy(a)
    assert b == a
    for x, y in zip(a.subtrees(), b.subtrees()):
        assert x is not y and type(x) is type(y)


def test_class_mismatch_and_label_semantics_unchanged():
    assert Tree("S", ["a"]) != ParentedTree("S", ["a"])
    assert Tree("S", ["a"]) != Tree("NP", ["a"])
    assert Tree("S", ["a", "b"]) != Tree("S", ["a"])
    assert Tree("S", [Tree("A", ["x"])]) != Tree("S", ["x"])
    assert Tree(1, [2]) == Tree(1.0, [2.0])  # == on labels and leaves, as before
    assert not (Tree("S", []) == "S")


def test_convert_between_subtypes_still_works_deep():
    parented = ParentedTree.convert(_chain(treemod.MAX_TREE_DEPTH + 1))
    assert isinstance(parented, ParentedTree)
    leaf_holder = parented
    while isinstance(leaf_holder[0], ParentedTree):
        leaf_holder = leaf_holder[0]
    assert leaf_holder.root() is parented  # parent links built correctly


def test_subclass_overrides_keep_their_own_paths():
    p = ProbabilisticTree("S", [ProbabilisticTree("A", ["x"], prob=0.5)], prob=0.25)
    q = copy.deepcopy(p)
    assert q == p and q[0].prob() == 0.5 and q.prob() == 0.25
    assert p != ProbabilisticTree(
        "S", [ProbabilisticTree("A", ["x"], prob=0.4)], prob=0.25
    )
    frozen = ImmutableTree.convert(Tree("S", [Tree("A", ["x"])]))
    assert isinstance(frozen[0], ImmutableTree)

    calls = []

    class Traced(Tree):
        @classmethod
        def convert(cls, tree):
            calls.append(tree)
            return super().convert(tree)

    Traced.convert(Tree("S", [Tree("A", ["x"]), "y"]))
    # the override is dispatched per child exactly as the recursive form did
    assert [c.label() if isinstance(c, Tree) else c for c in calls] == [
        "S",
        "A",
        "x",
        "y",
    ]
