"""
Tests for nltk.langnames module
"""

import unittest

from nltk.langnames import lang2q, q2tag, tag2q


class TestLangNames(unittest.TestCase):
    """Test language name utilities."""

    def test_tag2q_valid_tag(self):
        """Test tag2q with a valid BCP-47 tag."""
        result = tag2q("nds-u-sd-demv")
        assert result == "Q4289225"

    def test_tag2q_invalid_tag_returns_none(self):
        """Test tag2q returns None for invalid BCP-47 tag instead of raising KeyError."""
        result = tag2q("invalid-tag")
        assert result is None

    def test_tag2q_none_tag_returns_none(self):
        """Test tag2q handles None input gracefully."""
        result = tag2q(None)
        assert result is None

    def test_tag2q_empty_tag_returns_none(self):
        """Test tag2q handles empty string input gracefully."""
        result = tag2q("")
        assert result is None

    def test_lang2q_valid_name(self):
        """Test lang2q with a valid language name."""
        result = lang2q("Low German")
        assert result == "Q25433"

    def test_lang2q_invalid_name_returns_none(self):
        """Test lang2q returns None for invalid language name."""
        with self.assertWarns(UserWarning):
            result = lang2q("Invalid Language Name")
        assert result is None

    def test_q2tag_valid_qcode(self):
        """Test q2tag with a valid Q-code."""
        result = q2tag("Q4289225")
        assert result == "nds-u-sd-demv"

    def test_q2tag_invalid_qcode_returns_none(self):
        """Test q2tag returns None for invalid Q-code instead of raising KeyError."""
        result = q2tag("invalid-qcode")
        assert result is None

    def test_q2tag_none_qcode_returns_none(self):
        """Test q2tag handles None input gracefully."""
        result = q2tag(None)
        assert result is None

    def test_q2tag_empty_qcode_returns_none(self):
        """Test q2tag handles empty string input gracefully."""
        result = q2tag("")
        assert result is None
