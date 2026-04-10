"""
Tests for CCG semantics with alpha-equivalence.

Uses a "woman and cat" lexicon that follows standard CCG theory:
unary predicates for nouns (``\\x.cat(x)``), binary predicates for
transitive verbs (``\\x y.pet(y,x)``), and generalized quantifiers
for determiners (``\\P.the(P)``).

Tests verify that:
- ``compute_type_raised_semantics`` unwraps all outer lambda variables
  and lifts *F* inside, producing ``\\F x.F(body)`` rather than
  ``\\F.F(\\x.body)``.
- No spurious binary predicates (e.g. ``cat(x,z)``) appear for simple
  sentences (transitive verb without relative clauses).
- Reusing the same lexicon/parser across multiple sentences does not
  introduce free *F* variables (the mutation bug from issue #3345).
- ``Expression.alpha_normalize`` correctly canonicalizes bound variables.
"""

import unittest

from nltk.ccg import chart, lexicon


def _make_parser():
    """Build a CCGChartParser with the standard woman-and-cat lexicon."""
    lex = lexicon.fromstring(
        r"""
        :- S, NP, N

        V :: (S\NP)
        Vt :: ((S\NP)/NP)
        Det :: (NP/N)

        cat => N {\x.cat(x)}
        woman => N {\x.woman(x)}
        sleeps => V {\x.sleep(x)}
        pets => Vt {\x y.pet(y,x)}
        the => Det {\P.the(P)}
        of => ((N\N)/NP) {\e P x.(P(x) & belongs(x,e))}
        that => ((N\N)/(S/NP)) {\S P x.(P(x) & S(x))}
        """,
        True,
    )
    return chart.CCGChartParser(lex, chart.DefaultRuleSet)


def _unique_semantics(parser, sentence):
    """Return a sorted list of unique alpha-normalized semantics strings."""
    seen = set()
    for tree in parser.parse(sentence.split()):
        sem = tree.label()[0].semantics()
        if sem is not None:
            seen.add(str(sem.alpha_normalize()))
    return sorted(seen)


class TestCCGTypeRaisedSemantics(unittest.TestCase):
    """Verify compute_type_raised_semantics produces correct results."""

    def setUp(self):
        self.parser = _make_parser()

    def test_the_cat_sleeps(self):
        """Simple intransitive: ``the cat sleeps``."""
        sems = _unique_semantics(self.parser, "the cat sleeps")
        self.assertEqual(len(sems), 1)
        self.assertEqual(sems[0], r"sleep(the(\z1.cat(z1)))")

    def test_the_woman_pets_the_cat(self):
        """Transitive: ``the woman pets the cat``."""
        sems = _unique_semantics(self.parser, "the woman pets the cat")
        self.assertEqual(len(sems), 1)
        self.assertEqual(sems[0], r"pet(the(\z1.woman(z1)),the(\z2.cat(z2)))")

    def test_relative_clause_of(self):
        """Prepositional modifier: ``the cat of the woman sleeps``.

        The unwrapping form of type-raising produces 2 unique readings:
        the correct one and a spurious binary-predicate reading.
        """
        sems = _unique_semantics(self.parser, "the cat of the woman sleeps")
        self.assertEqual(len(sems), 2)
        correct = r"sleep(the(\z2.(cat(z2) & belongs(z2,the(\z1.woman(z1))))))"
        self.assertIn(correct, sems)

    def test_relative_clause_that(self):
        """Subject extraction: ``the cat that the woman pets sleeps``.

        The unwrapping form of type-raising produces 2 unique readings:
        the correct one and a spurious binary-predicate reading.
        """
        sems = _unique_semantics(self.parser, "the cat that the woman pets sleeps")
        self.assertEqual(len(sems), 2)
        correct = r"sleep(the(\z2.(cat(z2) & pet(the(\z1.woman(z1)),z2))))"
        self.assertIn(correct, sems)


class TestNoSpuriousBinaryPredicates(unittest.TestCase):
    """Ensure unary predicates stay unary after type-raising + composition."""

    def test_no_binary_cat(self):
        """``cat`` defined as ``\\x.cat(x)`` must not produce ``cat(x,z)``."""
        import re

        parser = _make_parser()
        for tree in parser.parse("the woman pets the cat".split()):
            sem_str = str(tree.label()[0].semantics())
            # Every cat(...) should have exactly one argument
            for m in re.finditer(r"cat\(([^)]*)\)", sem_str):
                args = m.group(1).split(",")
                self.assertEqual(
                    len(args), 1,
                    f"cat should be unary but got cat({m.group(1)}) in {sem_str}",
                )


class TestLexiconMutationBug(unittest.TestCase):
    """Regression test for issue #3345: type-raising must not mutate lexicon.

    When the same parser (and thus the same lexicon) is reused for multiple
    sentences, earlier parses must not corrupt later ones.
    """

    def test_no_free_F_variable(self):
        """Parsing multiple sentences must not leak free ``F`` variables."""
        parser = _make_parser()
        sentences = [
            "the cat of the woman sleeps",
            "the cat that the woman pets sleeps",
        ]
        for sentence in sentences:
            for tree in parser.parse(sentence.split()):
                sem = tree.label()[0].semantics()
                if sem is not None:
                    free_vars = {v.name for v in sem.free()}
                    for v in free_vars:
                        self.assertFalse(
                            v.startswith("F"),
                            f"Free variable '{v}' leaked in parse of "
                            f"'{sentence}': {sem}",
                        )

    def test_consistent_across_reuse(self):
        """Semantics must be the same whether the parser is fresh or reused."""
        parser = _make_parser()

        # Parse sentence 1 first (this triggered the mutation in the old code)
        list(parser.parse("the cat of the woman sleeps".split()))

        # Now parse sentence 2 with the *same* parser
        sems_reused = _unique_semantics(
            parser, "the cat that the woman pets sleeps"
        )

        # Parse sentence 2 with a *fresh* parser
        fresh_parser = _make_parser()
        sems_fresh = _unique_semantics(
            fresh_parser, "the cat that the woman pets sleeps"
        )

        self.assertEqual(sems_reused, sems_fresh)


class TestAlphaNormalize(unittest.TestCase):
    """Test Expression.alpha_normalize on lambda calculus expressions."""

    def test_alpha_equivalent_expressions(self):
        """Two alpha-equivalent expressions should normalize identically."""
        from nltk.sem.logic import Expression

        e1 = Expression.fromstring(r"\x.cat(x)")
        e2 = Expression.fromstring(r"\y.cat(y)")

        self.assertEqual(
            str(e1.alpha_normalize()),
            str(e2.alpha_normalize()),
        )

    def test_distinct_expressions_differ(self):
        """Non-equivalent expressions must normalize differently."""
        from nltk.sem.logic import Expression

        e1 = Expression.fromstring(r"\x.cat(x)")
        e2 = Expression.fromstring(r"\x.dog(x)")

        self.assertNotEqual(
            str(e1.alpha_normalize()),
            str(e2.alpha_normalize()),
        )

    def test_nested_lambda_normalize(self):
        """Nested lambdas should get canonical variable names."""
        from nltk.sem.logic import Expression

        e1 = Expression.fromstring(r"\x y.like(x,y)")
        e2 = Expression.fromstring(r"\a b.like(a,b)")

        self.assertEqual(
            str(e1.alpha_normalize()),
            str(e2.alpha_normalize()),
        )


if __name__ == "__main__":
    unittest.main()
