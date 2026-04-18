"""
Tests for the CCG (Combinatory Categorial Grammar) module.
"""

import unittest

from nltk.ccg.api import Direction, FunctionalCategory, PrimitiveCategory


class TestFunctionalCategoryCanUnifyDirection(unittest.TestCase):
    """`FunctionalCategory.can_unify` must propagate direction substitutions
    produced by `Direction.can_unify`. Without this, unifying a variable
    direction against a concrete one silently drops the binding, and the
    variable is never resolved during parsing.
    """

    def test_variable_direction_substitution_is_returned(self):
        """Regression test: previously, `can_unify` computed the direction
        substitution (`sd`) but its return statement omitted it
        (`return sa + sb`), so the caller never saw the `_` binding.
        """
        S = PrimitiveCategory("S")
        NP = PrimitiveCategory("NP")

        variable_cat = FunctionalCategory(S, NP, Direction("\\", "_"))
        concrete_cat = FunctionalCategory(S, NP, Direction("\\", ""))

        subs = variable_cat.can_unify(concrete_cat)

        self.assertIsNotNone(subs)
        self.assertIn(("_", ""), subs)

    def test_variable_direction_binds_to_concrete_modifier(self):
        """When the concrete side has a modifier (e.g. `.`), the `_` should
        bind to that modifier rather than an empty string.
        """
        S = PrimitiveCategory("S")
        NP = PrimitiveCategory("NP")

        variable_cat = FunctionalCategory(S, NP, Direction("/", "_"))
        concrete_cat = FunctionalCategory(S, NP, Direction("/", "."))

        subs = variable_cat.can_unify(concrete_cat)

        self.assertIsNotNone(subs)
        self.assertIn(("_", "."), subs)

    def test_matching_concrete_directions_still_unify(self):
        """Two matching concrete directions should still unify (returning
        no direction substitution), confirming the fix doesn't regress the
        non-variable path.
        """
        S = PrimitiveCategory("S")
        NP = PrimitiveCategory("NP")

        left = FunctionalCategory(S, NP, Direction("\\", ""))
        right = FunctionalCategory(S, NP, Direction("\\", ""))

        subs = left.can_unify(right)

        self.assertEqual(subs, [])
