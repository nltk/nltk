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
