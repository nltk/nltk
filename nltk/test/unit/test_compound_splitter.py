import unittest

from nltk.tokenize import WordNetCompoundSplitter, split_compound

try:
    from nltk.corpus import wordnet as wn

    wn.ensure_loaded()
    _WORDNET_AVAILABLE = True
except LookupError:
    _WORDNET_AVAILABLE = False


@unittest.skipUnless(_WORDNET_AVAILABLE, "WordNet resource not available")
class TestWordNetCompoundSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = WordNetCompoundSplitter()

    def test_preserves_known_word(self):
        self.assertEqual(self.splitter.split("region"), ["region"])

    def test_splits_compound_token(self):
        self.assertEqual(
            self.splitter.split("crossregionswitch"),
            ["cross", "region", "switch"],
        )

    def test_case_preservation(self):
        self.assertEqual(
            self.splitter.split("CrossRegionSwitch"),
            ["Cross", "Region", "Switch"],
        )

    def test_fallback_for_unknown(self):
        token = "foobarbaz"
        self.assertEqual(self.splitter.split(token), [token])

    def test_convenience_function(self):
        self.assertEqual(
            split_compound("crossregionswitch"),
            ["cross", "region", "switch"],
        )

    # Ensure harmless words remain unsplit.
    def test_prefers_unsplit_when_costs_tie(self):
        self.assertEqual(self.splitter.split("therapist"), ["therapist"])

    def test_keeps_palindrome_word(self):
        self.assertEqual(self.splitter.split("racecar"), ["racecar"])

    def test_keeps_common_word(self):
        self.assertEqual(self.splitter.split("network"), ["network"])

if __name__ == "__main__":
    unittest.main()
