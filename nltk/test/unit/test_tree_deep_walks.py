# Natural Language Toolkit: deepcopy depth regression test
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``Tree.convert`` (behind ``deepcopy``) recursed through a list comprehension,
a separate frame before Python 3.12, so on 3.10 and 3.11 it overflowed at
depth ~497, short of the ``MAX_TREE_DEPTH`` that ``fromstring`` and the
chomsky_normal_form guard accept."""

import copy

import pytest

from nltk.tree import ParentedTree, ProbabilisticTree, Tree
from nltk.tree import tree as treemod


def _chain(depth):
    t = Tree("L", ["w"])
    for _ in range(depth - 1):
        t = Tree("N", [t])
    return t


@pytest.mark.parametrize("depth", [treemod.MAX_TREE_DEPTH, treemod.MAX_TREE_DEPTH + 1])
def test_deepcopy_reaches_max_tree_depth(depth):
    tree = _chain(depth)
    twin = copy.deepcopy(tree)
    assert twin is not tree
    assert twin.height() == tree.height()
    assert twin.leaves() == ["w"]


def test_convert_output_unchanged():
    tree = Tree.fromstring("(S (NP (D the) (N cat)) (VP (V sat) (PP (P on) (NP mat))))")
    twin = copy.deepcopy(tree)
    assert twin == tree and str(twin) == str(tree)
    assert all(a is not b for a, b in zip(tree.subtrees(), twin.subtrees()))
    parented = ParentedTree.convert(tree)
    assert isinstance(parented[0][0], ParentedTree)
    assert parented[0][0].parent() is parented[0]
    prob = ProbabilisticTree("S", [ProbabilisticTree("A", ["x"], prob=0.5)], prob=0.25)
    assert copy.deepcopy(prob)[0].prob() == 0.5


_PROBE = """
import copy, sys
from nltk.tree import Tree
kind = sys.argv[1]
if kind == "chain":
    t = Tree("L", ["w"])
    for _ in range(5000):
        t = Tree("N", [t])
elif kind == "cycle":
    t = Tree("N", ["w"])
    t.append(t)
try:
    copy.deepcopy(t)
    print("ok")
except RecursionError:
    print("RecursionError")
"""


@pytest.mark.parametrize("kind", ["chain", "cycle"])
def test_over_limit_and_cyclic_trees_fail_cleanly(kind):
    # at the default recursion limit a tree too deep to copy, or one that
    # contains itself, must raise RecursionError, never crash the interpreter
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = str(Path(__file__).resolve().parents[3])
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, kind],
        capture_output=True,
        text=True,
        timeout=120,
        env=dict(os.environ, PYTHONPATH=root),
    )
    assert proc.returncode == 0, (proc.returncode, proc.stderr[-300:])
    assert proc.stdout.strip() == "RecursionError"


def test_shared_subtrees_copy_every_occurrence():
    # deepcopy ignores the memo, as before: a subtree referenced twice is
    # copied twice (cost grows with paths, not nodes; unchanged by this fix)
    shared = Tree("A", ["x"])
    tree = Tree("S", [shared, shared])
    twin = copy.deepcopy(tree)
    assert twin[0] == twin[1] and twin[0] is not twin[1]
