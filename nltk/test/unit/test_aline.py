# -*- coding: utf-8 -*-
"""
Unit tests for nltk.metrics.aline
"""

from __future__ import unicode_literals

import unittest

from nltk.metrics import aline


class TestAline(unittest.TestCase):
    """
    Test Aline algorithm for aligning phonetic sequences
    """

    def test_aline(self):
        result = aline.align('θin', 'tenwis')
        expected = [[('θ', 't'), ('i', 'e'), ('n', 'n'), ('-', 'w'), ('-', 'i'), ('-', 's')]]

        self.assertEqual(result, expected)

        result = aline.align('jo', 'ʒə')
        expected = [[('j', 'ʒ'), ('o', 'ə')]]

        self.assertEqual(result, expected)

        result = aline.align('pematesiweni', 'pematesewen')
        expected = [[('p', 'p'), ('e', 'e'), ('m', 'm'), ('a', 'a'), ('t', 't'), ('e', 'e'),
                     ('s', 's'), ('i', 'e'), ('w', 'w'), ('e', 'e'), ('n', 'n'), ('i', '-')]]

        self.assertEqual(result, expected)

        result = aline.align('tuwθ', 'dentis')
        expected = [[('t', 'd'), ('u', 'e'), ('w', '-'), ('-', 'n'), ('-', 't'), ('-', 'i'), ('θ', 's')]]

        self.assertEqual(result, expected)

    def test_aline_delta(self):
        """
        Test aline for computing the difference between two segments
        """
        result = aline.delta('p', 'q')
        expected = 20.0

        self.assertEqual(result, expected)

        result = aline.delta('a', 'A')
        expected = 0.0

        self.assertEqual(result, expected)
