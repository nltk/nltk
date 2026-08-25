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
            stemmer = SnowballStemmer(language)

            try:
                result = stemmer.stem("")
                self.assertEqual(
                    result,
                    "",
                    f"Stemmer for '{language}' failed to return empty string.",
                )
            except Exception as e:
                self.fail(
                    f"Stemmer for '{language}' raised {type(e).__name__} on empty string: {e}"
                )
