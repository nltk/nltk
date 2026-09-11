# Natural Language Toolkit: uncontrolled-recursion (CWE-674) attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack matrix for uncontrolled recursion (CWE-674) across NLTK.

Every parser / traversal helper bounded in this PR is driven with an
adversarially deep payload and must raise a *bounded* exception (``ValueError``
or ``LogicalExpressionException``), never an uncaught ``RecursionError`` and
never silent acceptance; benign inputs must still parse. A second block pins
parsers that were already bounded, so their coverage cannot silently regress.

Nothing is mocked: each case loads the real public API and runs it. Each guard
fires at a fixed depth below the interpreter recursion limit, so the
"even with a raised limit" case proves the module guard stops the walk rather
than luck with the ambient limit.
"""

import warnings
from xml.etree.ElementTree import Element, SubElement

import pytest

from nltk.sem.logic import LogicalExpressionException

#: Comfortably deeper than every guard (all <= 500) yet built iteratively, so at
#: the default recursion limit the guard fires before the interpreter would.
DEEP = 1500


def _deep_conll(n):
    rows = []
    for i in range(1, n + 1):
        head = i - 1
        rel = "ROOT" if i == 1 else "dep"
        rows.append(f"{i}\tw{i}\t_\tN\tN\t_\t{head}\t{rel}\t_\t_")
    return "\n".join(rows)


def _deep_xml(n, leaf_tag):
    root = Element("s")
    cur = root
    for _ in range(n):
        cur = SubElement(cur, "grp")
    SubElement(cur, leaf_tag)
    return root


def _attack_tree_fromlist():
    from nltk.tree import Tree

    payload = "leaf"
    for _ in range(DEEP):
        payload = ["N", payload]
    Tree.fromlist(payload)


def _attack_tree_fromstring():
    from nltk.tree import Tree

    Tree.fromstring("(S " * DEEP + "x" + ")" * DEEP)


def _attack_read_type():
    from nltk.sem.logic import read_type

    payload = "e"
    for _ in range(DEEP):
        payload = "<%s,e>" % payload
    read_type(payload)


def _attack_ccg_matchbrackets():
    from nltk.ccg.lexicon import matchBrackets

    matchBrackets("(" * DEEP + ")" * DEEP)


def _attack_ccg_augparse():
    from nltk.ccg.lexicon import augParseCategory

    augParseCategory("(" * DEEP + "S" + ")" * DEEP, ["S", "N"], {})


def _attack_toolbox_parse():
    from nltk.toolbox import ToolboxSettings

    data = "".join("\\+f%d val\n" % i for i in range(DEEP))
    ts = ToolboxSettings()
    ts.open_string(data)
    ts.parse()


def _attack_depgraph_triples():
    from nltk.parse.dependencygraph import DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_deep_conll(DEEP))
    list(dg.triples())


def _attack_depgraph_tree():
    from nltk.parse.dependencygraph import DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_deep_conll(DEEP))
    dg.tree()


def _attack_depgraph_cycle_path():
    from nltk.parse.dependencygraph import DependencyGraph

    dg = DependencyGraph()
    dg.nodes.clear()
    for i in range(DEEP):
        dg.nodes[i] = {
            "address": i,
            "word": "w%d" % i,
            "deps": [i + 1] if i + 1 < DEEP else [],
            "rel": "dep",
        }
    dg.get_cycle_path(dg.nodes[0], goal_node_index=-1)


def _attack_tgrep_parens():
    from nltk.tgrep import tgrep_compile

    tgrep_compile("(" * DEEP + "A" + ")" * DEEP)


def _attack_tgrep_brackets():
    from nltk.tgrep import tgrep_compile

    tgrep_compile("A" + "[" * DEEP + "]" * DEEP)


def _attack_bnc_xmlwords():
    from nltk.corpus.reader.bnc import _all_xmlwords_in

    _all_xmlwords_in(_deep_xml(DEEP, "w"))


def _attack_semcor_xmlwords():
    from nltk.corpus.reader.semcor import _all_xmlwords_in

    _all_xmlwords_in(_deep_xml(DEEP, "wf"))


#: name -> (attack callable, the bounded exception it must raise)
ATTACKS = {
    "tree.fromlist": (_attack_tree_fromlist, ValueError),
    "tree.fromstring": (_attack_tree_fromstring, ValueError),
    "logic.read_type": (_attack_read_type, LogicalExpressionException),
    "ccg.matchBrackets": (_attack_ccg_matchbrackets, ValueError),
    "ccg.augParseCategory": (_attack_ccg_augparse, ValueError),
    "toolbox.settings.parse": (_attack_toolbox_parse, ValueError),
    "depgraph.triples": (_attack_depgraph_triples, ValueError),
    "depgraph.tree": (_attack_depgraph_tree, ValueError),
    "depgraph.get_cycle_path": (_attack_depgraph_cycle_path, ValueError),
    "tgrep.parens": (_attack_tgrep_parens, ValueError),
    "tgrep.brackets": (_attack_tgrep_brackets, ValueError),
    "bnc._all_xmlwords_in": (_attack_bnc_xmlwords, ValueError),
    "semcor._all_xmlwords_in": (_attack_semcor_xmlwords, ValueError),
}


@pytest.mark.parametrize("key", sorted(ATTACKS))
def test_deep_input_raises_bounded_error_not_recursionerror(key):
    attack, exc_type = ATTACKS[key]
    with pytest.raises(exc_type) as caught:
        attack()
    assert not isinstance(caught.value, RecursionError), key


@pytest.mark.parametrize("key", sorted(ATTACKS))
def test_guard_fires_even_with_a_raised_recursion_limit(key):
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


# --- already-bounded parsers: pin the coverage so it cannot regress ----------


def _bounded_featstruct():
    from nltk.featstruct import FeatStruct

    FeatStruct("[a=" * DEEP + "1" + "]" * DEEP)


def _bounded_drt():
    from nltk.sem.drt import DrtExpression

    DrtExpression.fromstring("(" * DEEP + "P(x)" + ")" * DEEP)


def _bounded_logic_expr():
    from nltk.sem.logic import Expression

    Expression.fromstring("(" * DEEP + "P" + ")" * DEEP)


@pytest.mark.parametrize(
    "attack,exc_type",
    [
        (_bounded_featstruct, ValueError),
        (_bounded_drt, LogicalExpressionException),
        (_bounded_logic_expr, LogicalExpressionException),
    ],
)
def test_already_bounded_parsers_stay_bounded(attack, exc_type):
    with pytest.raises(exc_type) as caught:
        attack()
    assert not isinstance(caught.value, RecursionError)


# --- benign inputs must still work -------------------------------------------


def test_benign_tree():
    from nltk.tree import Tree

    assert Tree.fromstring("(S (NP I) (VP (V saw)))").label() == "S"
    assert isinstance(Tree.fromlist(["S", ["NP", "I"]]), Tree)


def test_benign_read_type():
    from nltk.sem.logic import read_type

    assert str(read_type("<e,<e,t>>")) == "<e,<e,t>>"


def test_benign_ccg():
    from nltk.ccg.lexicon import augParseCategory

    cat, _ = augParseCategory("(S/N)", ["S", "N"], {})
    assert str(cat) == "(S/N)"


def test_benign_toolbox():
    from nltk.toolbox import ToolboxSettings, remove_blanks

    ts = ToolboxSettings()
    ts.open_string("\\+record\n\\field one\n\\-record\n")
    tree = ts.parse()
    remove_blanks(tree)
    assert tree.tag == "record"


def test_benign_depgraph():
    from nltk.parse.dependencygraph import DependencyGraph

    conll = "1\tHi\t_\tUH\tUH\t_\t0\tROOT\t_\t_\n2\tthere\t_\tRB\tRB\t_\t1\tdep\t_\t_"
    dg = DependencyGraph(conll)
    assert list(dg.triples()) == [(("Hi", "UH"), "dep", ("there", "RB"))]
    assert dg.tree().label() == "Hi"


def test_benign_tgrep():
    from nltk.tgrep import tgrep_compile, tgrep_nodes
    from nltk.tree import ParentedTree

    tree = ParentedTree.fromstring("(S (NP (D the) (N dog)) (VP (V barks)))")
    assert callable(tgrep_compile("S < NP"))
    assert list(tgrep_nodes("NP < N", [tree]))
    assert callable(tgrep_compile("(" * 6 + "S" + ")" * 6))


def test_benign_xmlwords():
    from nltk.corpus.reader.bnc import _all_xmlwords_in as bnc_words
    from nltk.corpus.reader.semcor import _all_xmlwords_in as sem_words

    b = Element("s")
    SubElement(b, "w").text = "hi"
    SubElement(b, "c").text = "."
    assert len(bnc_words(b)) == 2
    s = Element("s")
    SubElement(s, "wf").text = "hi"
    SubElement(s, "punc").text = "."
    assert len(sem_words(s)) == 2
