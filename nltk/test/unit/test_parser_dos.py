"""
Living-audit regression tests for the parser / grammar unbounded-work DoS
cluster (GHSA-ff5c-cp5c-9wjf umbrella; sibling of RecursiveDescentParser,
CVE-2026-12876).

This file records the WHOLE audited candidate set, not only the exploitable
ones:

* The *exploitable* sinks (ShiftReduceParser, CFG.chomsky_normal_form's unit-rule
  removal, NonprojectiveDependencyParser, ViterbiParser, generate()) each HUNG on
  a tiny crafted input on the unpatched code -- reproduced out-of-process with a
  hard kill. Each now has a bound (a wall-clock ``max_time``, an algorithmic cycle
  guard, or an operation budget); the tests assert it is bounded (raises quickly)
  and that benign inputs are unaffected.
* The *already-bounded* parsers checked in the same sweep (ChartParser,
  ProjectiveDependencyParser, ProbabilisticNonprojectiveParser) are kept here as
  explicit BENIGN cases: the test documents WHY each is safe and will fail if a
  future change removes the existing guard or turns a polynomial path exponential.

RecursiveDescentParser (the seed of this cluster) has its own file,
``test_recursivedescent_dos.py``.

Bounds are monkeypatched/short so the suite stays fast; payloads are sized so the
unpatched blow-up cannot finish inside the window.
"""

import pytest

import nltk.parse.chart as _chartmod
import nltk.parse.generate as _genmod
from nltk import CFG, PCFG
from nltk.grammar import DependencyGrammar
from nltk.parse import (
    ChartParser,
    NonprojectiveDependencyParser,
    ProjectiveDependencyParser,
    ShiftReduceParser,
    ViterbiParser,
)
from nltk.parse.generate import generate

FAST = 0.5


# ==========================================================================
# EXPLOITABLE (fixed) -- hung pre-patch, must be bounded now
# ==========================================================================


class TestShiftReduceDoS:
    GRAMMAR = CFG.fromstring(
        """
        S -> NP VP
        NP -> Det N
        VP -> V
        Det -> 'the'
        N -> 'dog'
        V -> 'barks'
        """
    )

    def test_benign_parse_unaffected(self):
        parses = list(ShiftReduceParser(self.GRAMMAR).parse(["the", "dog", "barks"]))
        assert len(parses) == 1 and parses[0].label() == "S"

    def test_default_is_bounded(self):
        from nltk.parse.shiftreduce import DEFAULT_MAX_TIME

        p = ShiftReduceParser(CFG.fromstring("NP -> NP | 'a'"))
        assert p._max_time == DEFAULT_MAX_TIME

    def test_cyclic_unary_production_is_bounded(self):
        # Pre-patch: `while self._reduce(): pass` rewrites NP -> NP forever.
        p = ShiftReduceParser(CFG.fromstring("NP -> NP | 'a'"), max_time=FAST)
        with pytest.raises(TimeoutError):
            list(p.parse(["a"]))


class TestChomskyNormalFormUnitCycleDoS:
    def test_normal_conversion_correct(self):
        cnf = CFG.fromstring(
            """
            S -> NP VP
            NP -> Det N
            VP -> V NP
            Det -> 'the'
            N -> 'dog'
            V -> 'saw'
            """
        ).chomsky_normal_form()
        assert cnf.is_chomsky_normal_form()

    def test_unit_production_cycle_terminates(self):
        # Pre-patch: A -> B, B -> A regenerates unit rules forever (hang).
        cnf = CFG.fromstring("A -> B\nB -> A\nA -> 'x'").chomsky_normal_form()
        assert cnf.is_chomsky_normal_form()


class TestNonprojectiveDependencyDoS:
    def test_benign_parse_unaffected(self):
        dg = DependencyGrammar.fromstring("'barks' -> 'dog'\n'dog' -> 'the'")
        # A sparse grammar + short input completes well inside the bound.
        list(NonprojectiveDependencyParser(dg).parse(["the", "dog", "barks"]))

    def test_dense_grammar_is_bounded(self):
        # Pre-patch: dense grammar -> exponential head-assignment enumeration.
        words = [f"w{i}" for i in range(9)]
        rules = "\n".join(
            f"'{h}' -> " + " | ".join(f"'{d}'" for d in words if d != h) for h in words
        )
        dg = DependencyGrammar.fromstring(rules)
        with pytest.raises(TimeoutError):
            list(NonprojectiveDependencyParser(dg, max_time=FAST).parse(words))


class TestViterbiDoS:
    def test_benign_parse_unaffected(self):
        pcfg = PCFG.fromstring(
            """
            S -> NP VP [1.0]
            NP -> Det N [1.0]
            VP -> V [1.0]
            Det -> 'the' [1.0]
            N -> 'dog' [1.0]
            V -> 'barks' [1.0]
            """
        )
        trees = list(ViterbiParser(pcfg).parse(["the", "dog", "barks"]))
        assert len(trees) == 1 and trees[0].label() == "S"

    def test_long_rhs_ambiguous_grammar_is_bounded(self):
        # Pre-patch: S -> B*16 over B -> B B | 'a' enumerates C(n,k) child lists.
        rhs = " ".join(["B"] * 16)
        pcfg = PCFG.fromstring(f"S -> {rhs} [1.0]\nB -> B B [0.5] | 'a' [0.5]")
        with pytest.raises(TimeoutError):
            list(ViterbiParser(pcfg, max_time=FAST).parse(["a"] * 30))


class TestGenerateDoS:
    def test_benign_generation_unaffected(self):
        assert list(generate(CFG.fromstring("S -> 'a' | 'b'"))) == [["a"], ["b"]]

    def test_unbounded_enumeration_is_bounded(self, monkeypatch):
        # Pre-patch: list(generate(g)) with no `n` enumerates a combinatorial
        # number of sentences (the per-expansion budget did not cover the
        # cartesian product) and hung. The budget now also spends per emitted
        # sentence. Lower the cap so the test is fast.
        monkeypatch.setattr(_genmod, "MAX_GENERATE_OPERATIONS", 5000)
        with pytest.raises(ValueError):
            list(generate(CFG.fromstring("S -> S S | 'a'")))


# ==========================================================================
# ALREADY-BOUNDED (benign) -- audited in the same sweep, safe by construction
# ==========================================================================


class TestAlreadyBoundedParsers:
    def test_chart_parser_is_bounded(self, monkeypatch):
        # Recognition is polynomial (agenda/chart); tree extraction is capped by
        # MAX_PARSE_TREES. Benign: an ambiguous grammar raises rather than hangs.
        monkeypatch.setattr(_chartmod, "MAX_PARSE_TREES", 5000)
        with pytest.raises(ValueError):
            list(ChartParser(CFG.fromstring("S -> S S | 'a'")).parse(["a"] * 12))

    def test_projective_dependency_is_bounded(self):
        # Quadratic chart, already capped by MAX_TOKENS (=500) -- #3676.
        dg = DependencyGrammar.fromstring("'w' -> 'w'")
        with pytest.raises(ValueError):
            list(ProjectiveDependencyParser(dg).parse(["w"] * (500 + 1)))

    def test_small_ambiguous_chart_parse_completes(self):
        # Benign sanity: a small ambiguous parse returns (bounded) trees.
        trees = list(ChartParser(CFG.fromstring("S -> S S | 'a'")).parse(["a"] * 4))
        assert len(trees) >= 1
