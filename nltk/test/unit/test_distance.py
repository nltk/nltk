import unittest

from nltk.metrics.distance import edit_distance


class EditDistanceTestPattern:
    def __init__(
        self, s1, s2, expected_transpositions, expected_no_transpositions, sub_cost=1
    ):
        self.s1 = s1
        self.s2 = s2
        self.expected_tr = expected_transpositions
        self.expected_no_tr = expected_no_transpositions
        self.sub_cost = sub_cost

    def test_with_transpositions(self):
        self.assertEqual(
            edit_distance(
                self.s1, self.s2, substitution_cost=self.sub_cost, transpositions=True
            ),
            self.expected_tr,
        )
        self.assertEqual(
            edit_distance(
                self.s2, self.s1, substitution_cost=self.sub_cost, transpositions=True
            ),
            self.expected_tr,
        )

    def test_without_transpositions(self):
        self.assertEqual(
            edit_distance(
                self.s1, self.s2, substitution_cost=self.sub_cost, transpositions=False
            ),
            self.expected_no_tr,
        )
        self.assertEqual(
            edit_distance(
                self.s2, self.s1, substitution_cost=self.sub_cost, transpositions=False
            ),
            self.expected_no_tr,
        )


class TestEditDistanceABC(unittest.TestCase, EditDistanceTestPattern):
    def __init__(self, *args, **k_args):
        EditDistanceTestPattern.__init__(self, "abc", "ca", 2, 3)
        unittest.TestCase.__init__(self, *args, **k_args)


class TestEditDistanceWithHigherSubCost(unittest.TestCase, EditDistanceTestPattern):
    def __init__(self, *args, **k_args):
        EditDistanceTestPattern.__init__(self, "wants", "swim", 6, 7, sub_cost=2)
        unittest.TestCase.__init__(self, *args, **k_args)


class TestEditDistanceWithNoTranspositionBenefit(
    unittest.TestCase, EditDistanceTestPattern
):
    def __init__(self, *args, **k_args):
        EditDistanceTestPattern.__init__(self, "wants", "wasp", 3, 3)
        unittest.TestCase.__init__(self, *args, **k_args)
