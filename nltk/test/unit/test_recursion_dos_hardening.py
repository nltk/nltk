# Natural Language Toolkit: uncontrolled-recursion (CWE-674) attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack matrix for uncontrolled recursion (CWE-674) across NLTK.

Every raw-text parser / structure walker that recurses on untrusted input is
driven with an adversarially deep payload and must raise a *bounded* exception
(``ValueError`` or ``LogicalExpressionException``), never an uncaught
``RecursionError`` and never silent acceptance. Benign inputs must still parse.

Nothing is mocked: each case loads the real public API and runs it. Each guard
fires at a fixed depth below the interpreter recursion limit, so the
"even with a raised limit" case proves the module's own guard stops the walk
rather than luck with the ambient limit.
"""

import warnings

import pytest


# --- deep-input attacks (each must raise a bounded exception) ----------------


def _attack_tree_fromlist():
    from nltk.tree import Tree
    from nltk.tree.tree import MAX_TREE_DEPTH

    payload = "leaf"
    for _ in range(MAX_TREE_DEPTH + 500):
        payload = ["N", payload]
    Tree.fromlist(payload)


def _attack_tree_fromstring():
    from nltk.tree import Tree
    from nltk.tree.tree import MAX_TREE_DEPTH

    n = MAX_TREE_DEPTH + 500
    Tree.fromstring("(S " * n + "x" + ")" * n)


def _attack_read_type():
    from nltk.sem.logic import MAX_TYPE_DEPTH, read_type

    payload = "e"
    for _ in range(MAX_TYPE_DEPTH + 500):
        payload = "<%s,e>" % payload
    read_type(payload)


def _attack_ccg_matchbrackets():
    from nltk.ccg.lexicon import MAX_CATEGORY_DEPTH, matchBrackets

    n = MAX_CATEGORY_DEPTH + 500
    matchBrackets("(" * n + ")" * n)


def _attack_ccg_augparse():
    from nltk.ccg.lexicon import MAX_CATEGORY_DEPTH, augParseCategory

    n = MAX_CATEGORY_DEPTH + 500
    augParseCategory("(" * n + "S" + ")" * n, ["S", "N"], {})


def _attack_toolbox_settings():
    from nltk.toolbox import MAX_TOOLBOX_DEPTH, ToolboxSettings

    data = "".join("\\+f%d val\n" % i for i in range(MAX_TOOLBOX_DEPTH + 500))
    ts = ToolboxSettings()
    ts.open_string(data)
    ts.parse()


def _deep_conll(n):
    rows = []
    for i in range(1, n + 1):
        head = i - 1
        rel = "ROOT" if i == 1 else "dep"
        rows.append(f"{i}\tw{i}\t_\tN\tN\t_\t{head}\t{rel}\t_\t_")
    return "\n".join(rows)


def _attack_depgraph_triples():
    from nltk.parse.dependencygraph import MAX_GRAPH_DEPTH, DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_deep_conll(MAX_GRAPH_DEPTH + 500))
    list(dg.triples())


def _attack_depgraph_tree():
    from nltk.parse.dependencygraph import MAX_GRAPH_DEPTH, DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_deep_conll(MAX_GRAPH_DEPTH + 500))
    dg.tree()


def _attack_depgraph_cycle_path():
    from nltk.parse.dependencygraph import MAX_GRAPH_DEPTH, DependencyGraph

    dg = DependencyGraph()
    dg.nodes.clear()
    n = MAX_GRAPH_DEPTH + 500
    for i in range(n):
        dg.nodes[i] = {
            "address": i,
            "word": "w%d" % i,
            "deps": [i + 1] if i + 1 < n else [],
            "rel": "dep",
        }
    dg.get_cycle_path(dg.nodes[0], goal_node_index=-1)


def _attack_tgrep_parens():
    from nltk.tgrep import tgrep_compile

    n = 3000
    tgrep_compile("(" * n + "A" + ")" * n)


def _attack_tgrep_brackets():
    from nltk.tgrep import tgrep_compile

    n = 3000
    tgrep_compile("A" + "[" * n + "]" * n)


# id -> (attack callable, bounded exception types it must raise)
ATTACKS = {
    "tree.fromlist": (_attack_tree_fromlist, ValueError),
    "tree.fromstring": (_attack_tree_fromstring, ValueError),
    "logic.read_type": (_attack_read_type, Exception),
    "ccg.matchBrackets": (_attack_ccg_matchbrackets, ValueError),
    "ccg.augParseCategory": (_attack_ccg_augparse, ValueError),
    "toolbox.settings.parse": (_attack_toolbox_settings, ValueError),
    "depgraph.triples": (_attack_depgraph_triples, ValueError),
    "depgraph.tree": (_attack_depgraph_tree, ValueError),
    "depgraph.get_cycle_path": (_attack_depgraph_cycle_path, ValueError),
    "tgrep.parens": (_attack_tgrep_parens, ValueError),
    "tgrep.brackets": (_attack_tgrep_brackets, ValueError),
}


def _bounded_exc(key):
    return ATTACKS[key][1]


@pytest.mark.parametrize("key", sorted(ATTACKS))
def test_deep_input_raises_bounded_error_not_recursionerror(key):
    """A deep payload is rejected with a bounded exception, not RecursionError."""
    attack, exc_type = ATTACKS[key]
    with pytest.raises(exc_type) as caught:
        attack()
    assert not isinstance(caught.value, RecursionError), (
        "%s leaked an uncaught RecursionError (uncontrolled recursion)" % key
    )


@pytest.mark.parametrize("key", sorted(ATTACKS))
def test_guard_fires_even_with_a_raised_recursion_limit(key):
    """Prove the module guard (not the ambient limit) stops the walk.

    With the recursion limit raised well past each guard's fixed depth, the
    attack must still be refused with the same bounded exception; a fix that
    merely relied on the default limit would recurse further and crash here.
    """
    import sys

    attack, exc_type = ATTACKS[key]
    saved = sys.getrecursionlimit()
    sys.setrecursionlimit(20000)
    try:
        with pytest.raises(exc_type) as caught:
            attack()
        assert not isinstance(caught.value, RecursionError), key
    finally:
        sys.setrecursionlimit(saved)


# --- benign inputs must still work -------------------------------------------


def test_benign_tree_fromlist():
    from nltk.tree import Tree

    # fromlist repr()s each label, so the label is "'S'"; assert structure.
    tree = Tree.fromlist(["S", ["NP", "I"], ["VP", ["V", "saw"]]])
    assert isinstance(tree, Tree) and len(tree) == 2


def test_benign_tree_fromstring():
    from nltk.tree import Tree

    assert Tree.fromstring("(S (NP I) (VP (V saw) (NP him)))").label() == "S"


def test_benign_read_type():
    from nltk.sem.logic import read_type

    assert str(read_type("<e,<e,t>>")) == "<e,<e,t>>"


def test_benign_ccg_augparse():
    from nltk.ccg.lexicon import augParseCategory

    cat, _ = augParseCategory("(S/N)", ["S", "N"], {})
    assert str(cat) == "(S/N)"


def test_benign_toolbox_settings():
    from nltk.toolbox import ToolboxSettings, remove_blanks

    ts = ToolboxSettings()
    ts.open_string("\\+record\n\\field one\n\\-record\n")
    tree = ts.parse()
    remove_blanks(tree)
    assert tree.tag == "record"


def test_benign_depgraph_triples_and_tree():
    from nltk.parse.dependencygraph import DependencyGraph

    conll = (
        "1\tHi\t_\tUH\tUH\t_\t0\tROOT\t_\t_\n"
        "2\tthere\t_\tRB\tRB\t_\t1\tdep\t_\t_"
    )
    dg = DependencyGraph(conll)
    assert list(dg.triples()) == [(("Hi", "UH"), "dep", ("there", "RB"))]
    assert dg.tree().label() == "Hi"


def test_benign_tgrep():
    from nltk.tgrep import tgrep_compile, tgrep_nodes
    from nltk.tree import ParentedTree

    tree = ParentedTree.fromstring("(S (NP (D the) (N dog)) (VP (V barks)))")
    assert callable(tgrep_compile("S < NP"))
    assert list(tgrep_nodes("NP < N", [tree]))
    # a moderately nested but legitimate pattern parses fine
    assert callable(tgrep_compile("(" * 6 + "S" + ")" * 6))
