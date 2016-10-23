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
        
        result = aline.align('wən', 'unus')
        expected = [[('ə', 'u'), ('n', 'n'), ('-', 'u'), ('-', 's')]]
        self.assertEqual(result, expected)
        
        result = aline.align('flow', 'fluere')
        expected = [[('f', 'f'), ('l', 'l'), ('o', 'u'), ('w', '-'), ('-', 'e'), ('-', 'r'), ('-', 'e')]]
        self.assertEqual(result, expected)
        
        result = aline.align('wat', 'vas')
        expected = [[('w', 'v'), ('a', 'a'), ('t', 's')]]
        self.assertEqual(result, expected)
        
        result = aline.align('boka', 'buʃ')
        expected = [[('b', 'b'), ('o', 'u'), ('k', 'ʃ'), ('a', '-')]]
        self.assertEqual(result, expected)
        
        result = aline.align('ombre', 'om')
        expected = [[('o', 'o'), ('m', 'm'), ('b', '-'), ('r', '-'), ('e', '-')]]
        self.assertEqual(result, expected)
        
        result = aline.align('feðər', 'fEdər')
        expected = [[('f', 'f'), ('e', 'E'), ('ð', 'd'), ('ə', 'ə'), ('r', 'r')]]
        self.assertEqual(result, expected)
        
        
        
        
