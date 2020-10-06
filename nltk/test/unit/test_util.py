# -*- coding: utf-8 -*-
"""
Unit tests for nltk.util.
"""

import unittest
from nltk.util import everygrams


class TestEverygrams(unittest.TestCase):

    def setUp(self):
        """Form test data for tests."""
        self.test_data = iter('a b c'.split())

    def test_everygrams_without_padding(self):
        expected_output = [
            ('a',),
            ('a', 'b'),
            ('a', 'b', 'c'),
            ('b',),
            ('b', 'c'),
            ('c',),
        ]
        output = everygrams(self.test_data)
        self.assertCountEqual(output, expected_output)

    def test_everygrams_max_len(self):
        expected_output = [('a',), ('a', 'b'), ('b',), ('b', 'c'),('c',),]
        output = everygrams(self.test_data, max_len=2)
        self.assertCountEqual(output, expected_output)

    def test_everygrams_min_len(self):
        expected_output = [('a', 'b'), ('b', 'c'), ('a', 'b', 'c'),]
        output = everygrams(self.test_data, min_len=2)
        self.assertCountEqual(output, expected_output)

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
        output = everygrams(self.test_data, max_len=3, pad_right=True)
        self.assertCountEqual(output, expected_output)

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
        output = everygrams(self.test_data, max_len=3, pad_left=True)
        self.assertCountEqual(output, expected_output)
