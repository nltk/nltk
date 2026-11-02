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

The second half of this file checks real parse trees, not only the attack
shape: every Penn Treebank sample tree, a ViterbiParser and InsideChartParser
parse (nested ProbabilisticTree, whose repr appends ``(p=...)`` at every
level), the frozen form (``[p]`` at every level), and a subclass with its own
``__repr__`` as a child. The expected strings were captured from develop
before the rewrite, so they are independent of the implementation under test.
"""

import pytest

from nltk.grammar import PCFG
from nltk.parse.pchart import InsideChartParser
from nltk.parse.viterbi import ViterbiParser
from nltk.tree import ImmutableProbabilisticTree, ProbabilisticTree, Tree
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


def _treebank_trees():
    from nltk.corpus import treebank

    try:
        return list(treebank.parsed_sents())
    except LookupError:
        pytest.skip("treebank corpus not installed")


def test_every_treebank_tree_renders_as_before():
    """Every Penn Treebank sample tree: repr equals the recursive form it
    replaced, ``eval(repr(t))`` rebuilds an equal tree, and ``str(t)`` still
    round-trips through ``Tree.fromstring``. Rendering stays byte-identical on
    real parses, not only on the synthetic deep chain.
    """
    trees = _treebank_trees()
    assert len(trees) > 3000
    for tree in trees:
        rendered = repr(tree)
        assert rendered == _recursive_repr(tree)
        assert eval(rendered, {"Tree": Tree}) == tree
        assert Tree.fromstring(str(tree)) == tree


# The PCFG from nltk.parse.viterbi.demo and the rendering develop produced.
_TOY_PCFG = PCFG.fromstring(
    """
    S -> NP VP [1.0]
    NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
    Det -> 'the' [0.8] | 'my' [0.2]
    N -> 'man' [0.5] | 'telescope' [0.5]
    VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
    V -> 'ate' [0.35] | 'saw' [0.65]
    PP -> P NP [1.0]
    P -> 'with' [0.61] | 'under' [0.39]
    """
)
_SENT = ["I", "saw", "the", "man", "with", "my", "telescope"]
_VITERBI_REPR = (
    "ProbabilisticTree('S', [ProbabilisticTree('NP', ['I']) (p=0.15), "
    "ProbabilisticTree('VP', [ProbabilisticTree('V', ['saw']) (p=0.65), "
    "ProbabilisticTree('NP', [ProbabilisticTree('NP', [ProbabilisticTree('Det', "
    "['the']) (p=0.8), ProbabilisticTree('N', ['man']) (p=0.5)]) (p=0.2), "
    "ProbabilisticTree('PP', [ProbabilisticTree('P', ['with']) (p=0.61), "
    "ProbabilisticTree('NP', [ProbabilisticTree('Det', ['my']) (p=0.2), "
    "ProbabilisticTree('N', ['telescope']) (p=0.5)]) (p=0.05)]) (p=0.0305)]) "
    "(p=0.001525)]) (p=0.0006938749999999999)]) (p=0.00010408124999999999)"
)
_VITERBI_STR = """(S
  (NP I)
  (VP
    (V saw)
    (NP
      (NP (Det the) (N man))
      (PP (P with) (NP (Det my) (N telescope)))))) (p=0.000104081)"""
_FROZEN_REPR = (
    "ImmutableProbabilisticTree('S', [ImmutableProbabilisticTree('NP', ['I']) "
    "[0.15], ImmutableProbabilisticTree('VP', [ImmutableProbabilisticTree('V', "
    "['saw']) [0.65], ImmutableProbabilisticTree('NP', "
    "[ImmutableProbabilisticTree('NP', [ImmutableProbabilisticTree('Det', "
    "['the']) [0.8], ImmutableProbabilisticTree('N', ['man']) [0.5]]) [0.2], "
    "ImmutableProbabilisticTree('PP', [ImmutableProbabilisticTree('P', "
    "['with']) [0.61], ImmutableProbabilisticTree('NP', "
    "[ImmutableProbabilisticTree('Det', ['my']) [0.2], "
    "ImmutableProbabilisticTree('N', ['telescope']) [0.5]]) [0.05]]) [0.0305]]) "
    "[0.001525]]) [0.0006938749999999999]]) [0.00010408124999999999]"
)
_FROZEN_STR = _VITERBI_STR.replace("(p=0.000104081)", "[0.00010408124999999999]")


def test_viterbi_parse_repr_and_str_match_develop():
    """A real ViterbiParser parse is a ProbabilisticTree at every level and
    its repr carries ``(p=...)`` at every level, as on develop.

    Teeth: an iterative walk that formats children with the base Tree format
    drops every inner probability; this literal catches that.
    """
    (parse,) = ViterbiParser(_TOY_PCFG).parse(_SENT)
    assert isinstance(parse, ProbabilisticTree)
    assert repr(parse) == _VITERBI_REPR
    assert str(parse) == _VITERBI_STR


def test_frozen_parse_repr_and_str_match_develop():
    """``freeze()`` gives an ImmutableProbabilisticTree whose repr appends
    ``[p]`` at every level and whose str appends it once, as on develop."""
    (parse,) = ViterbiParser(_TOY_PCFG).parse(_SENT)
    frozen = parse.freeze()
    assert isinstance(frozen, ImmutableProbabilisticTree)
    assert repr(frozen) == _FROZEN_REPR
    assert str(frozen) == _FROZEN_STR


def test_chart_parses_render_a_probability_on_every_node():
    """InsideChartParser parses (the pchart demo) render one ``(p=`` per
    subtree in repr and exactly one in str."""
    parses = list(InsideChartParser(_TOY_PCFG).parse(_SENT))
    assert len(parses) == 2
    for parse in parses:
        assert repr(parse).count(" (p=") == len(list(parse.subtrees()))
        assert str(parse).count(" (p=") == 1
        assert str(parse).startswith("(S")


def test_child_subclass_with_its_own_repr_is_rendered_by_it():
    """A subclass that overrides __repr__ (not the hook) is still rendered by
    its own method when it appears as a child, as ``repr(c)`` did before."""

    class Loud(Tree):
        def __repr__(self):
            return "<loud " + Tree.__repr__(self) + ">"

    tree = Tree("S", [Loud("A", ["x"]), "z"])
    assert repr(tree) == "Tree('S', [<loud Loud('A', ['x'])>, 'z'])"
    nested = Loud("S", [Loud("A", ["x"]), Tree("B", ["q"])])
    assert (
        repr(nested) == "<loud Loud('S', [<loud Loud('A', ['x'])>, Tree('B', ['q'])])>"
    )


def test_deep_probabilistic_tree_repr_does_not_overflow_the_stack():
    """A ProbabilisticTree chain below MAX_TREE_DEPTH reprs with a ``(p=`` at
    every level, frozen too. Teeth: with the suffix added in a __repr__
    override that calls Tree.__repr__, every level costs two Python frames
    and develop raises RecursionError at this depth on CPython 3.10 and
    3.13 alike.
    """
    depth = MAX_TREE_DEPTH - 50
    tree = ProbabilisticTree("x", ["y"], prob=0.5)
    for _ in range(depth - 1):
        tree = ProbabilisticTree("x", [tree], prob=0.5)
    assert repr(tree).count(" (p=0.5)") == depth
    assert repr(tree.freeze()).count("]) [0.5]") == depth
    assert str(tree).count("(x") == depth


def _all_tree_subclasses():
    import nltk.parse
    import nltk.tree

    found = set()
    stack = [Tree]
    while stack:
        for sub in stack.pop().__subclasses__():
            in_library = sub.__module__.startswith("nltk.") and not (
                sub.__module__.startswith("nltk.test")
            )
            if sub not in found and in_library:
                found.add(sub)
                stack.append(sub)
    return sorted(found, key=lambda c: (c.__module__, c.__name__))


def test_every_tree_subclass_renders_a_child_as_it_renders_a_root():
    """Every Tree subclass in the nltk library (found by walking
    ``__subclasses__`` after importing the tree and parse packages; classes a
    test defines locally are skipped, since ``__subclasses__`` holds them until
    garbage collection, which the free-threaded build defers) renders
    identically as a root and as a child, of itself and of a plain Tree. This is the invariant the
    base-format walk broke for the probabilistic classes; it holds for any
    subclass, whether it decorates via ``_repr_node`` or defines ``__repr__``,
    and does not depend on the hook existing.
    """
    subclasses = _all_tree_subclasses()
    names = {cls.__name__ for cls in subclasses}
    assert {
        "ImmutableTree",
        "ImmutableProbabilisticTree",
        "ImmutableParentedTree",
        "ImmutableMultiParentedTree",
        "ParentedTree",
        "MultiParentedTree",
        "ProbabilisticTree",
    } <= names
    for cls in subclasses:
        kwargs = {"prob": 0.5} if "Probabilistic" in cls.__name__ else {}
        inner = cls("N", ["y"], **kwargs)
        outer = cls("N", [inner], **kwargs)
        plain = Tree("S", [cls("N", ["z"], **kwargs)])
        assert repr(outer).startswith(f"{cls.__name__}('N', [{inner!r}])"), cls
        assert repr(plain) == f"Tree('S', [{plain[0]!r}])", cls
        assert str(outer).startswith("(N (N y))"), cls
