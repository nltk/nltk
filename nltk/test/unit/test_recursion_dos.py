"""
Living-audit regression tests for the recursion / inefficient-complexity DoS
findings across the wider tree (GHSA-ff5c-cp5c-9wjf umbrella; CWE-674 / 407 /
400). These sit alongside the parser cluster in ``test_parser_dos.py`` and the
seed ``test_recursivedescent_dos.py``.

Each sink below was reproduced on the unpatched code (out-of-process with a hard
kill): ``ResolutionProver`` hung *uninterruptibly*, while ``FeatStructReader``,
``LogicParser`` and ``Tree.fromstring`` raised an unhandled ``RecursionError``
on a small crafted string. Each now aborts with a clean, bounded error and
benign inputs are unaffected.
"""

import pytest

import nltk.inference.resolution as _resolution
from nltk.featstruct import FeatStruct, FeatStructReader
from nltk.grammar import FeatureGrammar
from nltk.inference import ResolutionProver
from nltk.sem import Expression
from nltk.sem.logic import LogicalExpressionException
from nltk.tree import Tree


class TestResolutionUnifyDoS:
    def test_benign_proof(self):
        proved = ResolutionProver().prove(
            Expression.fromstring("mortal(socrates)"),
            [
                Expression.fromstring("all x.(man(x) -> mortal(x))"),
                Expression.fromstring("man(socrates)"),
            ],
        )
        assert proved is True

    def test_exponential_unify_is_time_bounded(self, monkeypatch):
        # Pre-patch: a single unify() of two clauses sharing many same-predicate
        # literals is super-exponential and UNINTERRUPTIBLE -- the between-call
        # TIMEOUT never fires. The deadline is now checked inside the unify
        # recursion. Lower TIMEOUT so the test is fast.
        monkeypatch.setattr(_resolution.ResolutionProver, "TIMEOUT", 1.0)
        k = 6
        c1 = "(" + "|".join(f"P(x{i})" for i in range(k)) + ")"
        c2 = "(" + "|".join(f"-P(y{i})" for i in range(k)) + ")"
        # Must RETURN (bounded) rather than hang; the goal is not provable here.
        result = ResolutionProver().prove(
            Expression.fromstring("Q(c)"),
            [Expression.fromstring(c1), Expression.fromstring(c2)],
        )
        assert result is False


class TestFeatStructReaderRecursion:
    def test_benign_parse(self):
        fs = FeatStruct("[a=1, b=[c=2], d={1, 2}]")
        assert fs["a"] == 1

    def test_reentrant_structure_still_parses(self):
        assert FeatStruct("(1)[a->(1)]") is not None

    @pytest.mark.parametrize(
        "payload",
        [
            "[a=" * 300 + "[]" + "]" * 300,  # feature dicts
            "[" * 300 + "]" * 300,  # feature lists
            "[a=" + "{" * 300 + "}" * 300 + "]",  # sets
            "[a=" + "(" * 300 + ")" * 300 + "]",  # tuples
        ],
    )
    def test_deep_nesting_raises_valueerror(self, payload):
        with pytest.raises(ValueError):
            FeatStruct(payload)

    def test_feature_grammar_entry_is_guarded(self):
        # FeatureGrammar.fromstring routes productions through the reader.
        with pytest.raises(ValueError):
            FeatureGrammar.fromstring("S -> X" + "[a=" * 300 + "[]" + "]" * 300)

    def test_max_depth_constant_present(self):
        assert 0 < FeatStructReader.MAX_DEPTH <= 500


class TestLogicParserOperatorChain:
    def test_benign_parse(self):
        e = Expression.fromstring("all x.(man(x) -> mortal(x))")
        assert str(e.simplify())
        assert str(Expression.fromstring("a & b & c")) == "(a & b & c)"

    @pytest.mark.parametrize("type_check", [False, True])
    def test_long_operator_chain_raises(self, type_check):
        # Pre-patch: a flat 'a & a & ...' chain bypassed MAX_PARSE_DEPTH (which
        # only counts parser-stack depth) and built an AST deep enough that
        # str()/simplify()/variables() raised RecursionError.
        s = " & ".join(["a"] * 500)
        with pytest.raises(LogicalExpressionException):
            Expression.fromstring(s, type_check=type_check)


class TestTreeFromstringDepth:
    def test_benign_parse(self):
        tree = Tree.fromstring("(S (NP the dog) (VP ran))")
        assert tree.label() == "S"

    def test_deep_nesting_raises_valueerror(self):
        # Pre-patch: the (iterative) parse builds an arbitrarily deep tree, then
        # every recursive traversal (str/productions/subtrees/...) crashes.
        import nltk.tree.tree as _treemod

        deep = (
            "(X " * (_treemod.MAX_TREE_DEPTH + 100)
            + "leaf"
            + ")" * (_treemod.MAX_TREE_DEPTH + 100)
        )
        with pytest.raises(ValueError):
            Tree.fromstring(deep)
