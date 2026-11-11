import unittest

from nltk.sentiment.util import extract_bigram_feats, extract_unigram_feats


class ExtractFeatsTest(unittest.TestCase):
    document = "the film was not good , not good at all".split()

    def test_unigram_feats(self):
        self.assertEqual(
            extract_unigram_feats(self.document, ["good", "bad", "film"]),
            {"contains(good)": True, "contains(bad)": False, "contains(film)": True},
        )

    def test_unigram_feats_with_negation(self):
        feats = extract_unigram_feats(
            self.document, ["good", "good_NEG"], handle_negation=True
        )
        self.assertEqual(feats, {"contains(good)": False, "contains(good_NEG)": True})

    def test_bigram_feats(self):
        bigrams = [("not", "good"), ("good", "not"), ("good", "at"), ("film", "not")]
        self.assertEqual(
            extract_bigram_feats(self.document, bigrams),
            {
                "contains(not - good)": True,
                "contains(good - not)": False,
                "contains(good - at)": True,
                "contains(film - not)": False,
            },
        )
