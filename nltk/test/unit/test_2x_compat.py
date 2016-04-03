# -*- coding: utf-8 -*-
"""
Unit tests for nltk.compat.
See also nltk/test/compat.doctest.
"""
from __future__ import absolute_import, unicode_literals
import unittest

from nltk.text import Text
from nltk.compat import PY3, python_2_unicode_compatible

def setup_module(module):
    from nose import SkipTest
    if PY3:
        raise SkipTest("test_2x_compat is for testing nltk.compat under Python 2.x")


class TestTextTransliteration(unittest.TestCase):
    txt = Text(["São", "Tomé", "and", "Príncipe"])

    def test_repr(self):
        self.assertEqual(repr(self.txt), br"<Text: S\xe3o Tom\xe9 and Pr\xedncipe...>")

    def test_str(self):
        self.assertEqual(str(self.txt), b"<Text: Sao Tome and Principe...>")


class TestFraction(unittest.TestCase):
    def test_unnoramlize_fraction(self):
        from fractions import Fraction as NativePythonFraction
        from nltk.compat import Fraction as NLTKFraction
        
        # The native fraction should throw a TypeError in Python < 3.5
        with self.assertRaises(TypeError):
            NativePythonFraction(0, 1000, _normalize=False)
        
        # Using nltk.compat.Fraction in Python < 3.5
        compat_frac = NLTKFraction(0, 1000, _normalize=False)
        # The numerator and denominator does not change. 
        assert compat_frac.numerator == 0
        assert compat_frac.denominator == 1000
        # The floating point value remains normalized. 
        assert float(compat_frac) == 0.0
        
        # Checks that the division is not divided by 
        # # by greatest common divisor (gcd).
        six_twelve = NLTKFraction(6, 12, _normalize=False)
        assert six_twelve.numerator == 6
        assert six_twelve.denominator == 12
        
        one_two = NLTKFraction(1, 2, _normalize=False)
        assert one_two.numerator == 1
        assert one_two.denominator == 2
        
        # Checks against the native fraction.
        six_twelve_original = NativePythonFraction(6, 12)
        # Checks that rational values of one_two and six_twelve is the same.
        assert float(one_two) == float(six_twelve) == float(six_twelve_original)
        
        # Checks that the fraction does get normalized, even when
        # _normalize == False when numerator is using native 
        # fractions.Fraction.from_float 
        assert NLTKFraction(3.142, _normalize=False) == NativePythonFraction(3.142)
