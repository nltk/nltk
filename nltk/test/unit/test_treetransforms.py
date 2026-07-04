"""Regression tests for the quadratic-time DoS in
``nltk.tree.Tree.un_chomsky_normal_form`` (CWE-407).

The un-binarisation pass removed each artificial Chomsky-Normal-Form node from
its parent with ``parent.index(node)`` / ``parent.remove(...)``. Because ``Tree``
subclasses ``list``, those compare children by value via the recursive
``Tree.__eq__``, rescanning a child list that grows wide as nodes are spliced
out -- O(n^2) over the artificial nodes (worse with deep subtrees). The pass now
rebuilds each parent's child list in a single left-to-right sweep (O(n)),
producing identical output for any tree in Chomsky Normal Form.
"""

import multiprocessing
import os

from nltk.tree import Tree
from nltk.tree.transforms import chomsky_normal_form, un_chomsky_normal_form

_TREES = [
    "(S (NP (D the) (N cat)) (VP (V sat)))",
    "(S (A a) (B b) (C c) (D d))",
    "(S (NP (D the) (Adj big) (N dog)) (VP (V ran) (PP (P to) (NP home))))",
]


def test_un_chomsky_roundtrips_chomsky_normal_form():
    """un_chomsky_normal_form must invert chomsky_normal_form for both factors."""
    for source in _TREES:
        for factor in ("right", "left"):
            tree = Tree.fromstring(source)
            expected = Tree.fromstring(source)
            chomsky_normal_form(tree, factor=factor)
            un_chomsky_normal_form(tree)
            assert tree == expected


def test_un_chomsky_collapses_artificial_node():
    """An artificial ``|`` node is spliced into its parent (children in order)."""
    tree = Tree.fromstring("(S (A a) (S|<B-C> (B b) (C c)))")
    un_chomsky_normal_form(tree)
    assert tree == Tree.fromstring("(S (A a) (B b) (C c))")


def test_chomsky_normal_form_with_terminal_siblings():
    """A terminal sitting beside subtrees must not crash chomsky_normal_form."""
    for factor in ("right", "left"):
        tree = Tree.fromstring("(S (S 1) + (S 2))")
        expected = Tree.fromstring("(S (S 1) + (S 2))")
        chomsky_normal_form(tree, factor=factor)
        for subtree in tree.subtrees():
            assert len(subtree) <= 2
        un_chomsky_normal_form(tree)
        assert tree == expected


def test_chomsky_normal_form_with_nonstring_terminal():
    """A non-string terminal (e.g. an int) among siblings must not crash."""
    for factor in ("right", "left"):
        tree = Tree("S", [Tree("A", ["a"]), 7, Tree("B", ["b"]), Tree("C", ["c"])])
        chomsky_normal_form(tree, factor=factor)
        for subtree in tree.subtrees():
            assert len(subtree) <= 2


def _un_chomsky_worker(n):
    """Un-binarise a large right-branching CNF tree; exit 0 ok, 3 on error."""
    try:
        payload = "(S (A a) " + "(S| (A a) " * n + "(A a)" + ")" * (n + 1)
        Tree.fromstring(payload).un_chomsky_normal_form()
        os._exit(0)
    except BaseException:
        os._exit(3)


def test_un_chomsky_is_linear_not_quadratic():
    """A large CNF tree must un-binarise quickly (linear), not tie up a core.

    Run in a spawned process with a hard deadline: the single-sweep pass returns
    in milliseconds, while the previous O(n^2) version needs over a minute at
    this size, so a regression is terminated instead of burning CPU for the rest
    of the suite.
    """
    n = 20_000
    deadline = 30
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_un_chomsky_worker, args=(n,))
    proc.start()
    proc.join(deadline)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "un_chomsky_normal_form did not finish in time: quadratic blow-up regressed"
        )
    assert proc.exitcode == 0, f"worker failed (exit {proc.exitcode})"
