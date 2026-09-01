import unittest

from nltk.stem.snowball import SnowballStemmer


class TestSnowballStemmer(unittest.TestCase):
    """Unit tests for the Snowball stemmer family."""

    def test_empty_string_handling(self):
        """
        Verify that stemming an empty string returns an empty string without
        crashing (CVE-2026-14597). Tests all supported Snowball languages.
        """
        for language in SnowballStemmer.languages:
            with self.subTest(language=language):
                stemmer = SnowballStemmer(language)
                self.assertEqual(
                    stemmer.stem(""),
                    "",
                    f"Stemmer for '{language}' failed to return empty string.",
                )
