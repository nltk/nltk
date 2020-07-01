# -*- coding: utf-8 -*-
"""
Unit tests for nltk.util.
"""

import unittest
from nltk.util import everygrams


class TestEverygrams(unittest.TestCase):
    # test_data = 'a b c'.split()

    # @classmethod
    def setUp(self):
        """Form test data for tests."""
        self.test_data = 'a b c'.split()

    def test_everygrams_pad_left(self):
        expected_output = set(
            [
                (None),
                (None, None),
                (None, None, 'a'),
                (None),
                (None, 'a'),
                (None, 'a', 'b'),
                ('a',),
                ('a', 'b'),
                ('a', 'b', 'c'),
                ('b',),
                ('b', 'c'),
                ('c',),
            ]
        )
        output = list(everygrams(self.test_data, max_len=3, pad_left=True))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

    def test_everygrams(self):
        test_data = 'a b c'.split()
        # Test everygrams with defaults.
        expected_output = set(
            [
                ('a',),
                ('a', 'b'),
                ('a', 'b', 'c'),
                ('b',),
                ('b', 'c'),
                ('c',),
            ]
        )
        output = list(everygrams(self.test_data))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

        # Test that everygrams works with iterables.
        output = list(everygrams(iter(test_data)))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

        # Test everygrams with a max length of 2.
        expected_output = set([('a',), ('a', 'b'), ('b',), ('b', 'c'),('c',),])
        output = list(everygrams(self.test_data, max_len=2))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

        # Test everygrams with a max length of 2.
        expected_output = set([('a', 'b'), ('b', 'c'), ('a', 'b', 'c'),])
        output = list(everygrams(self.test_data, min_len=2))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

    def test_everygrams_pad_right(self):
        expected_output = [
            ('a',),
            ('a', 'b'),
            ('a', 'b', 'c'),
            ('b',),
            ('b', 'c'),
            ('b', 'c', None),
            ('c',),
            ('c', None),
            ('c', None, None),
            (None,),
            (None, None),
            (None,),
        ]
        output = list(everygrams(self.test_data, max_len=3, pad_right=True))
        # Test for expected output.
        self.assertEqual(set(output), set(expected_output))
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))


    def test_everygrams_pad_left(self):
        expected_output = [
            (None,),
            (None, None),
            (None, None, 'a'),
            (None,),
            (None, 'a'),
            (None, 'a', 'b'),
            ('a',),
            ('a', 'b'),
            ('a', 'b', 'c'),
            ('b',),
            ('b', 'c'),
            ('c',),
        ]
        output = list(everygrams(self.test_data, max_len=3, pad_left=True))
        # Test for expected output.
        self.assertEqual(set(output), set(expected_output))
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))

    def test_everygrams_iterable(self):
        test_data = 'a b c'.split()
        # Test everygrams with defaults.
        expected_output = set(
            [
                ('a',),
                ('a', 'b'),
                ('a', 'b', 'c'),
                ('b',),
                ('b', 'c'),
                ('c',),
            ]
        )

        # Test that everygrams works with iterables.
        output = list(everygrams(iter(test_data)))
        # Test for expected output.
        self.assertEqual(set(output), expected_output)
        # Test that no grams are repeated.
        self.assertEqual(len(output), len(expected_output))
