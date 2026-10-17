"""Red-team algodos suite (2026-10-16): regex ReDoS, algorithmic (super-linear)
DoS and uncontrolled recursion in entry points NOT already covered by the
existing advisory probes.

Every REFUSED row asserts the SPECIFIC bounded refusal (exception type + message
fragment) of a public entry point on an adversarial-but-ordinary-shaped input.
Every BENIGN-OK row proves the guard does not over-block legitimate use, and the
scaling rows judge cost by CPU-time ratio over a 4x input (never absolute wall
clock), using nltk.test.unit.timing.

Runs on python3.13 AND python3.10:
    python3.13 -m pytest nltk/test/unit/test_attack_algodos.py
  -p no:cacheprovider \

No network, no filesystem, no tkinter, no pytest-timeout dependency. The attacks
are all in-memory and the capped sinks refuse in milliseconds, so no subprocess
is needed; the one scaling test is bounded by its own CPU-ratio assertion.
"""

import warnings

import pytest

from nltk.test.unit.timing import assert_subquadratic

# REFUSED: depth-capped recursion entry points. Each builds a far-past-cap
# input and asserts the bounded ValueError or parser refusal (CWE-674), so no
# RecursionError or crash escapes.


def test_tree_fromstring_deep_refused():
    """Tree.fromstring refuses an adversarially deep bracketing (MAX_TREE_DEPTH)."""
    from nltk.tree import Tree

    payload = "(" * 4000 + "x y" + ")" * 4000
    with pytest.raises(ValueError, match="MAX_TREE_DEPTH"):
        Tree.fromstring(payload)


def test_tree_fromlist_deep_refused():
    """Tree.fromlist refuses an adversarially deep nested list (MAX_TREE_DEPTH)."""
    from nltk.tree import Tree

    lst = "x"
    for _ in range(4000):
        lst = ["n", lst]
    with pytest.raises(ValueError, match="MAX_TREE_DEPTH"):
        Tree.fromlist(lst)


@pytest.mark.parametrize(
    "payload",
    [
        "(" * 4000 + "P" + ")" * 4000,  # deep parenthesisation
        "-" * 4000 + "P",  # deep negation
        "&".join(["P"] * 4000),  # deep conjunction chain
    ],
)
def test_logic_parser_deep_refused(payload):
    """LogicParser.parse refuses deeply nested expressions (max depth 200)."""
    from nltk.sem.logic import LogicalExpressionException, LogicParser

    with pytest.raises(
        LogicalExpressionException, match="nesting exceeds the maximum depth"
    ):
        LogicParser().parse(payload)


def test_featstruct_deep_refused():
    """FeatStruct refuses an adversarially deep nested feature structure (MAX_DEPTH)."""
    from nltk.featstruct import FeatStruct

    payload = "[a=" * 2000 + "1" + "]" * 2000
    with pytest.raises(ValueError, match="nesting depth exceeds MAX_DEPTH"):
        FeatStruct(payload)


def _long_chain(n):
    """An n-token linear Malt-TAB dependency chain (w1 root, w_i head w_{i-1})."""
    lines = ["w1\tX\t0\tROOT"] + [f"w{i}\tX\t{i-1}\tdep" for i in range(2, n + 1)]
    return "\n".join(lines) + "\n"


def test_depgraph_tree_deep_refused():
    """DependencyGraph.tree() refuses a 3000-token linear chain (MAX_DEPTH=200)."""
    from nltk.parse.dependencygraph import DependencyGraph

    dg = DependencyGraph(_long_chain(3000))
    with pytest.raises(ValueError, match="MAX_DEPTH"):
        dg.tree()


def test_depgraph_triples_deep_refused():
    """DependencyGraph.triples() refuses a 3000-token linear chain (MAX_DEPTH=200)."""
    from nltk.parse.dependencygraph import DependencyGraph

    dg = DependencyGraph(_long_chain(3000))
    with pytest.raises(ValueError, match="MAX_DEPTH"):
        list(dg.triples())


# --------------------------------------------------------------------------
# REFUSED: algorithmic (memory) DoS guard.
# --------------------------------------------------------------------------


def test_everygrams_default_unbounded_refused():
    """everygrams() with the default max_len refuses a long sequence (CWE-770).

    The default enumerates O(n**2) tuples (O(n**3) elements); the guard refuses
    it past MAX_EVERYGRAMS_DEFAULT_LEN rather than exhausting memory.
    """
    from nltk.util import MAX_EVERYGRAMS_DEFAULT_LEN, everygrams

    seq = list(range(MAX_EVERYGRAMS_DEFAULT_LEN + 50))
    with pytest.raises(ValueError, match="exhaust memory|max_len"):
        list(everygrams(seq))


# REFUSED: caller-supplied regex patterns go through nltk.redos, whose
# wall-clock timeout bounds a hostile match; assert the TimedPattern is wired
# up on a user tokenizer pattern.


def test_regexp_tokenizer_pattern_is_timeout_guarded():
    """RegexpTokenizer compiles the caller pattern through redos (TimedPattern),
    so a match carries a wall-clock timeout rather than running unbounded."""
    from nltk.redos import TimedPattern
    from nltk.tokenize import RegexpTokenizer

    tok = RegexpTokenizer(r"\w+")
    tok._check_regexp()
    assert isinstance(tok._regexp, TimedPattern)
    assert tok.tokenize("hello world foo") == ["hello", "world", "foo"]


# BENIGN-OK: legitimate inputs are accepted and correct, legal-but-large
# inputs scale linearly, so the guards above do not over-block.


def test_word_tokenize_correctness_benign():
    """word_tokenize produces the expected tokens on an ordinary sentence."""
    from nltk.tokenize import word_tokenize

    out = word_tokenize("The dog, a good boy, didn't run.")
    assert out == ["The", "dog", ",", "a", "good", "boy", ",", "did", "n't", "run", "."]


def test_word_tokenize_scales_linearly_benign():
    """word_tokenize on honest long text scales linearly (sub-quadratic) over 4x.

    Judged by CPU-time ratio with doubling/4x input, not wall clock.
    """
    from nltk.tokenize import word_tokenize

    base = "The quick brown fox, jumps! over 'the' lazy (dog) -- again. "
    small = base * 1000
    big = base * 4000
    assert_subquadratic(lambda s: word_tokenize(s), small, big, cpu_bound=True)


def test_depgraph_small_tree_and_triples_benign():
    """A short, legal dependency chain yields a correct tree and triples."""
    from nltk.parse.dependencygraph import DependencyGraph
    from nltk.tree import Tree

    dg = DependencyGraph(_long_chain(5))
    t = dg.tree()
    assert isinstance(t, Tree)
    assert t.label() == "w1"
    assert len(list(dg.triples())) == 4


def test_tree_under_cap_traversals_benign():
    """A legal tree at depth just under MAX_TREE_DEPTH traverses without crashing.

    Covers the traversals that ARE bounded by the cap on every supported
    interpreter: treepositions, subtrees, productions and str()/pformat. It does
    NOT assert repr(), which overflows the stack at depth ~200 on CPython <= 3.12
    even though the parser accepts depth 499 (see LEAK_tree_repr_recursion.py).
    """
    from nltk.tree import Tree

    depth = 450
    t = Tree.fromstring("(" * depth + "x y" + ")" * depth)
    assert len(t.treepositions()) >= depth
    assert len(list(t.subtrees())) >= depth
    assert len(t.productions()) >= depth
    assert isinstance(str(t), str)


def test_contains_cycle_listshaped_detects_benign():
    """contains_cycle() correctly detects a cycle on list-shaped deps (the form
    its docstring documents). Recorded here to contrast the dict-shaped defect
    captured in LEAK_contains_cycle_dead_on_parsed.py."""
    from nltk.parse.dependencygraph import DependencyGraph

    d = DependencyGraph()
    d.nodes = {
        0: {"word": None, "deps": [1], "rel": "TOP", "address": 0},
        1: {"word": None, "deps": [2], "rel": "N", "address": 1},
        2: {"word": None, "deps": [4], "rel": "N", "address": 2},
        3: {"word": None, "deps": [1], "rel": "N", "address": 3},
        4: {"word": None, "deps": [3], "rel": "N", "address": 4},
    }
    d.root = d.nodes[0]
    assert d.contains_cycle() == [1, 2, 4, 3]


def test_contains_cycle_acyclic_benign():
    """contains_cycle() returns False on an acyclic parsed chain (true negative)."""
    from nltk.parse.dependencygraph import DependencyGraph

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dg = DependencyGraph(_long_chain(20))
    assert dg.contains_cycle() is False


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
