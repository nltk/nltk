# Natural Language Toolkit: Tree.__repr__ recursion-depth regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Regression tests for uncontrolled recursion in Tree.__repr__ (CWE-674).

Tree.fromstring / fromlist cap nesting at MAX_TREE_DEPTH (500) and the module
states that keeps every traversal safe. Tree.__repr__ recursed once per level
(``", ".join(repr(c) for c in self)``, a frame per level plus the generator),
so on CPython 3.12 and earlier ``repr(tree)`` raised an uncaught RecursionError
at a depth around 200, far below the cap, while ``str()`` / ``pformat`` /
``treepositions`` / ``subtrees`` / ``productions`` (explicit loops) survived to
the cap. A caller reaching the crash needs only an accepted bracketed string of
ordinary depth and any code that reprs it: ``%r``, a REPL echo,
``logging(..., tree)``, repr of a container of trees, or a tree in an exception
message. __repr__ now walks an explicit stack and produces identical output.
"""

import pytest

from nltk.tree import Tree
from nltk.tree.tree import MAX_TREE_DEPTH


def _recursive_repr(tree):
    """The old recursive repr, kept here as the oracle the fix must match."""
    childstr = ", ".join(
        _recursive_repr(child) if isinstance(child, Tree) else repr(child)
        for child in tree
    )
    return f"{type(tree).__name__}({tree._label!r}, [{childstr}])"


@pytest.mark.parametrize(
    "tree",
    [
        Tree.fromstring("(S (NP (DT the) (NN dog)) (VP (VBD barked)))"),
        Tree.fromstring("(ROOT (X a))"),
        Tree("S", [Tree("NP", ["the", "dog"]), "x", Tree("VP", [Tree("V", ["ran"])])]),
    ],
)
def test_repr_matches_the_recursive_form(tree):
    """The iterative repr is byte-identical to the recursive repr it replaced."""
    assert repr(tree) == _recursive_repr(tree)


def test_repr_of_a_deep_accepted_tree_does_not_overflow_the_stack():
    """repr() of a tree the parser accepts (depth below MAX_TREE_DEPTH) must not
    raise RecursionError on any supported interpreter.

    Teeth: at this depth the old recursive repr raised an uncaught
    RecursionError on CPython <= 3.12 (while str() survived), so this test fails
    on those interpreters without the iterative rewrite.
    """
    depth = MAX_TREE_DEPTH - 50
    tree = Tree.fromstring("(" * depth + "x y" + ")" * depth)
    rendered = repr(tree)
    assert rendered.startswith("Tree(")
    assert rendered.count("Tree(") == depth


def test_str_and_repr_agree_on_depth_with_traversals():
    """repr now survives the same depth str() and the other traversals already do."""
    depth = MAX_TREE_DEPTH - 50
    tree = Tree.fromstring("(" * depth + "x y" + ")" * depth)
    assert isinstance(str(tree), str)
    assert len(tree.treepositions()) >= depth
    assert len(list(tree.subtrees())) >= depth
    assert isinstance(repr(tree), str)


def test_repr_shares_a_repeated_subtree_without_duplicating_cost():
    """A subtree referenced twice renders correctly (the stack walk is by node)."""
    sub = Tree("A", ["x"])
    tree = Tree("Z", [sub, sub])
    assert repr(tree) == "Tree('Z', [Tree('A', ['x']), Tree('A', ['x'])])"
