import unittest

from nltk.ccg import chart, lexicon


class TestCCGFeatureStructures(unittest.TestCase):
    def test_parse_feature_structure_category(self):
        lex = lexicon.fromstring(
            r"""
            :- S, NP
            he => NP[AGR=sg,CASE=nom]
            """
        )

        category = lex.categories("he")[0].categ()

        self.assertEqual(category.features()["AGR"], "sg")
        self.assertEqual(category.features()["CASE"], "nom")

    def test_feature_structure_unification_rejects_conflicting_values(self):
        lex = lexicon.fromstring(
            r"""
            :- S, NP
            he => NP[AGR=sg]
            they => NP[AGR=pl]
            eats => S\NP[AGR=sg]
            """
        )

        subject = lex.categories("he")[0].categ()
        plural_subject = lex.categories("they")[0].categ()
        verb_argument = lex.categories("eats")[0].categ().arg()

        self.assertEqual(verb_argument.can_unify(subject), [])
        self.assertIsNone(verb_argument.can_unify(plural_subject))

    def test_feature_variable_bindings_substitute_into_result(self):
        lex = lexicon.fromstring(
            r"""
            :- S, NP
            agreed => S[AGR=?a]\NP[AGR=?a]
            he => NP[AGR=sg]
            """
        )

        verb = lex.categories("agreed")[0].categ()
        subject = lex.categories("he")[0].categ()

        substitutions = verb.arg().can_unify(subject)
        result = verb.res().substitute(substitutions)

        self.assertEqual(result.features()["AGR"], "sg")

    def test_parser_uses_feature_structures_for_agreement(self):
        lex = lexicon.fromstring(
            r"""
            :- S, NP
            he => NP[AGR=sg]
            they => NP[AGR=pl]
            eats => S\NP[AGR=sg]
            eat => S\NP[AGR=pl]
            """
        )
        parser = chart.CCGChartParser(lex, chart.ApplicationRuleSet)

        self.assertEqual(len(list(parser.parse("he eats".split()))), 1)
        self.assertEqual(len(list(parser.parse("they eat".split()))), 1)
        self.assertEqual(list(parser.parse("they eats".split())), [])


if __name__ == "__main__":
    unittest.main()
