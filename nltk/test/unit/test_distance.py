import unittest
from nltk.metrics.distance import edit_distance


class TestEditDistanceABC(unittest.TestCase):

    def setUp(self):
        self.left = "abc"
        self.right = "ca"

    def test_with_transpositions(self):
        self.assertEqual(edit_distance(self.left, self.right, transpositions=True), 2)
        self.assertEqual(edit_distance(self.right, self.left, transpositions=True), 2)

    def test_without_transpositions(self):
        self.assertEqual(edit_distance(self.left, self.right, transpositions=False), 3)
        self.assertEqual(edit_distance(self.right, self.left, transpositions=False), 3)


class TestEditDistanceWithHigherSubCost(unittest.TestCase):

    def setUp(self):
        self.left = "wants"
        self.right = "Wasp"
        self.sub_cost = 2

    def test_with_transpositions(self):
        self.assertEqual(edit_distance(self.left, self.right, substitution_cost=2, transpositions=True), 4)
        self.assertEqual(edit_distance(self.right, self.left, substitution_cost=2, transpositions=True), 4)

    def test_without_transpositions(self):
        self.assertEqual(edit_distance(self.left, self.right, substitution_cost=2, transpositions=False), 5)
        self.assertEqual(edit_distance(self.right, self.left, substitution_cost=2, transpositions=False), 5)

