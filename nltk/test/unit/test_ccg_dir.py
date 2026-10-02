import unittest

from nltk.ccg import lexicon
from nltk.ccg.api import Direction, FunctionalCategory, PrimitiveCategory


class TestCCGDirection(unittest.TestCase):

    # --- Parser and Unification Tests (PR #3556) ---

    def test_parse_variable_direction(self):
        """
        Ensures the string parser can successfully instantiate a Direction object
        that correctly identifies as a variable.
        """
        lex_str = r"""
        :- S, NP
        quickly => (S\_NP)/(S\_NP)
        """
        lex = lexicon.fromstring(lex_str)

        quickly_token = lex.categories("quickly")[0]
        quickly_cat = quickly_token.categ()
        var_direction = quickly_cat.res().dir()

        self.assertTrue(
            var_direction.is_variable(),
            "Lexer failed to properly parse the direction as a variable.",
        )
        self.assertEqual(
            var_direction.restrs(),
            "_",
            f"Expected restriction '_', got {var_direction.restrs()!r}",
        )

    def test_variable_direction_can_unify(self):
        """
        Ensures that when a variable direction unifies with a concrete direction,
        the substitution mapping is correctly extracted and returned to the caller.
        """
        lex_str = r"""
        :- S, NP
        walked => S\NP
        quickly => (S\_NP)/(S\_NP)
        """
        lex = lexicon.fromstring(lex_str)

        walked_cat = lex.categories("walked")[0].categ()
        quickly_cat = lex.categories("quickly")[0].categ()

        subs = quickly_cat.res().can_unify(walked_cat)

        self.assertIsNotNone(subs, "Unification failed entirely.")
        substituted_vars = [var for var, val in subs]
        self.assertIn(
            "_", substituted_vars, "can_unify dropped the direction variable mapping!"
        )

    def test_strict_regex_rejects_double_variable(self):
        r"""
        Ensures that the stricter APP_RE regex rejects invalid consecutive
        variable modalities (e.g., `\__`).
        """
        lex_str = r"""
        :- S, NP
        bad_word => (S\__NP)/(S\_NP)
        """
        with self.assertRaises(AttributeError):
            lex = lexicon.fromstring(lex_str)

    def test_direction_equality_and_hashing(self):
        """
        Ensures that a parsed variable direction (instantiated with a regex tuple)
        and a hand-constructed variable direction (instantiated with a string)
        evaluate as equal and share the same hash.
        """
        manual_dir = Direction("\\", "_")
        parsed_dir = Direction("\\", ("_", ""))

        self.assertEqual(
            manual_dir,
            parsed_dir,
            "Directions with coerced tuples do not evaluate as equal!",
        )
        self.assertEqual(
            hash(manual_dir),
            hash(parsed_dir),
            "Directions with coerced tuples do not hash equally!",
        )

    # --- Substitution Tests (PR #3547 & Legacy) ---

    def test_substitute_applies_to_direction(self):
        """
        Direction substitutions must propagate through substitute().
        Regression test updated to expect string restrictions instead of lists.
        """
        res = PrimitiveCategory("S")
        arg = PrimitiveCategory("NP")
        variable_dir = Direction("/", "_")
        category = FunctionalCategory(res, arg, variable_dir)

        # Replaced list ["."] with string "."
        new_restrictions = "."
        subs = [("_", new_restrictions)]
        result = category.substitute(subs)

        self.assertFalse(result.dir().is_variable())
        self.assertEqual(result.dir().restrs(), new_restrictions)

    def test_substitute_no_op_on_concrete_direction(self):
        """
        Substitution on a non-variable direction should be a no-op.
        Regression test updated to pass and expect string restrictions.
        """
        res = PrimitiveCategory("S")
        arg = PrimitiveCategory("NP")
        # Replaced list ["."] with string "."
        concrete_dir = Direction("\\", ".")
        category = FunctionalCategory(res, arg, concrete_dir)

        result = category.substitute([("_", ",")])

        self.assertEqual(result.dir().restrs(), ".")


if __name__ == "__main__":
    unittest.main()
