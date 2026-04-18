"""
Tests for the CCG (Combinatory Categorial Grammar) module.
"""

import unittest

from nltk.ccg.api import Direction


class TestDirectionTupleRestrictions(unittest.TestCase):
    """`Direction.__init__` must treat a raw regex-capture tuple (as produced
    by the lexicon's `APP_RE`) as equivalent to its collapsed string form.
    Otherwise variable directions parsed from strings never test as variable.
    """

    def test_tuple_restrictions_normalize_to_string(self):
        """Regression test: previously, passing `('_', '')` left `_restrs`
        as a tuple, so `is_variable()` always returned False for parsed
        variable directions.
        """
        parsed = Direction("\\", ("_", ""))
        self.assertTrue(parsed.is_variable())
        self.assertEqual(parsed.restrs(), "_")

    def test_tuple_and_string_directions_are_equal(self):
        """Directions built from a tuple and from a string should compare
        and hash identically once normalized.
        """
        from_parser = Direction("\\", ("_", ""))
        from_user = Direction("\\", "_")
        self.assertEqual(from_parser, from_user)
        self.assertEqual(hash(from_parser), hash(from_user))

    def test_tuple_concrete_modifier_preserved(self):
        """A concrete modifier captured as a tuple (e.g. ('.', '')) should
        normalize to '.', not read as variable.
        """
        d = Direction("/", (".", ""))
        self.assertFalse(d.is_variable())
        self.assertEqual(d.restrs(), ".")

    def test_empty_tuple_restrictions(self):
        """An empty modifier tuple should behave like no restrictions."""
        d = Direction("/", ("", ""))
        self.assertFalse(d.is_variable())
        self.assertEqual(d.restrs(), "")
