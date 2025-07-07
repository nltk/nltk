"""
Unit tests for nltk.langnames module.

Tests for language name and code lookup functions with improved error handling.
"""

import unittest
import warnings
import pytest

from nltk.langnames import langname, langcode


class TestLangname(unittest.TestCase):
    """Tests for the langname() function."""

    def test_valid_retired_code(self):
        """Test that valid retired codes return correct language names."""
        result = langname('fri')
        self.assertEqual(result, 'Western Frisian')

    def test_valid_short_code(self):
        """Test that valid 3-letter codes work correctly."""
        # This should work and may produce a warning about shortening
        with warnings.catch_warnings(record=True) as w:
            result = langname('eng')
            self.assertIsNotNone(result)
            # Check if shortening warning was issued
            if w:
                self.assertIn('Shortening', str(w[0].message))

    def test_invalid_code_returns_none(self):
        """Test that invalid language codes return None instead of raising KeyError."""
        with warnings.catch_warnings(record=True) as w:
            result = langname('xyz')
            self.assertIsNone(result)
            # Should emit a warning
            self.assertTrue(len(w) > 0)

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        with warnings.catch_warnings(record=True) as w:
            result = langname('')
            self.assertIsNone(result)
            # Should emit a warning
            self.assertTrue(len(w) > 0)
            self.assertIn('Could not find code', str(w[0].message))

    def test_non_string_input_handling(self):
        """Test behavior with non-string inputs."""
        # Test with None - should raise AttributeError 
        with self.assertRaises(AttributeError):
            langname(None)
        
        # Test with numbers - should raise AttributeError
        with self.assertRaises(AttributeError):
            langname(123)

    def test_exceptionally_long_string(self):
        """Test behavior with very long strings."""
        long_string = 'x' * 1000
        with warnings.catch_warnings(record=True) as w:
            result = langname(long_string)
            self.assertIsNone(result)

    def test_typ_parameter_full(self):
        """Test typ='full' parameter."""
        result = langname('fri', typ='full')
        self.assertEqual(result, 'Western Frisian')

    def test_typ_parameter_short(self):
        """Test typ='short' parameter."""
        result = langname('fri', typ='short')
        self.assertEqual(result, 'Western Frisian')

    def test_composite_bcp47_tag(self):
        """Test composite BCP-47 tag handling."""
        # Test with a composite tag that should work
        with warnings.catch_warnings(record=True):
            result = langname('en-US')
            # Should return some result or None, but not raise an exception
            self.assertIsInstance(result, (str, type(None)))


class TestLangcode(unittest.TestCase):
    """Tests for the langcode() function."""

    def test_valid_retired_language_name(self):
        """Test that valid retired language names return correct codes."""
        result = langcode('Western Frisian')
        self.assertEqual(result, 'fy')

    def test_invalid_language_name_returns_none(self):
        """Test that invalid language names return None instead of raising KeyError."""
        with warnings.catch_warnings(record=True) as w:
            result = langcode('InvalidLanguageName')
            self.assertIsNone(result)
            # Should emit a warning
            self.assertTrue(len(w) > 0)
            self.assertIn('Could not find language', str(w[0].message))

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        with warnings.catch_warnings(record=True) as w:
            result = langcode('')
            self.assertIsNone(result)
            # Should emit a warning
            self.assertTrue(len(w) > 0)
            self.assertIn('Could not find language', str(w[0].message))

    def test_non_string_input_handling(self):
        """Test behavior with non-string inputs."""
        # Test with None - should emit warning and return None
        with warnings.catch_warnings(record=True) as w:
            result = langcode(None)
            self.assertIsNone(result)

        # Test with numbers - should emit warning and return None
        with warnings.catch_warnings(record=True) as w:
            result = langcode(123)
            self.assertIsNone(result)

        # Test with list - should raise TypeError since lists are unhashable
        with self.assertRaises(TypeError):
            langcode(['English'])

    def test_exceptionally_long_string(self):
        """Test behavior with very long strings."""
        long_string = 'English' + 'x' * 1000
        with warnings.catch_warnings(record=True) as w:
            result = langcode(long_string)
            self.assertIsNone(result)

    def test_typ_parameter_default(self):
        """Test default typ=2 parameter returns 2-letter code."""
        result = langcode('Western Frisian')
        self.assertEqual(result, 'fy')
        self.assertEqual(len(result), 2)

    def test_typ_parameter_3(self):
        """Test typ=3 parameter returns 3-letter code when available."""
        result = langcode('Western Frisian', typ=3)
        # For Western Frisian, should get 3-letter code if available
        self.assertIsNotNone(result)

    def test_case_sensitivity(self):
        """Test case sensitivity in language names."""
        # Test exact case
        result1 = langcode('Western Frisian')
        self.assertIsNotNone(result1)
        
        # Test different case - should return None since lookup is case-sensitive
        with warnings.catch_warnings(record=True):
            result2 = langcode('western frisian')
            self.assertIsNone(result2)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error conditions."""

    def test_special_characters_in_input(self):
        """Test handling of special characters."""
        special_inputs = ['lang@name', 'lang#name', 'lang$name', 'lang%name']
        for special_input in special_inputs:
            with warnings.catch_warnings(record=True):
                result_name = langname(special_input)
                result_code = langcode(special_input)
                # Should return None for invalid inputs
                self.assertIsNone(result_name)
                self.assertIsNone(result_code)

    def test_unicode_input(self):
        """Test handling of unicode characters."""
        unicode_inputs = ['语言', 'язык', 'Språk']
        for unicode_input in unicode_inputs:
            with warnings.catch_warnings(record=True):
                result_name = langname(unicode_input)
                result_code = langcode(unicode_input)
                # Should return None for unknown unicode inputs
                self.assertIsNone(result_name)
                self.assertIsNone(result_code)

    def test_whitespace_only_input(self):
        """Test handling of whitespace-only strings."""
        whitespace_inputs = [' ', '\t', '\n', '   ', '\t\n ']
        for ws_input in whitespace_inputs:
            with warnings.catch_warnings(record=True):
                result_name = langname(ws_input)
                result_code = langcode(ws_input)
                # Should return None for whitespace-only inputs
                self.assertIsNone(result_name)
                self.assertIsNone(result_code)


if __name__ == '__main__':
    unittest.main()