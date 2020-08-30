import unittest
from nltk.sentiment.vader import SentimentIntensityAnalyzer


class TestVader(unittest.TestCase):
    def setUp(self):
        self.si = SentimentIntensityAnalyzer()

    def test_polarity_score(self):
        pos = "The food is great"
        neg = "The service is horrible"

        pos_score = self.si.polarity_scores(pos)
        neg_score = self.si.polarity_scores(neg)

        self.assertEqual(pos_score["compound"], 0.6249)
        self.assertEqual(neg_score["compound"], -0.5423)

    def test_booster_boosts_the_score(self):
        pos = "The food is really great"
        neg = "The service is really horrible"

        pos_score = self.si.polarity_scores(pos)
        neg_score = self.si.polarity_scores(neg)

        self.assertEqual(pos_score["compound"], 0.659)
        self.assertEqual(neg_score["compound"], -0.5849)

    def test_punctuation_increases_the_score(self):
        line = "The food is great!"
        scores = self.si.polarity_scores(line)
        self.assertEqual(scores["compound"], 0.6588)

    def test_but_can_flip_the_polarity(self):
        no_but = "The food is great, and the service is horrible"
        but = "The food is great, but the service is horrible"

        no_but_score = self.si.polarity_scores(no_but)
        but_score = self.si.polarity_scores(but)

        self.assertEqual(no_but_score["compound"], 0.1531)
        # "but" puts more emphasis on second half of sentence
        self.assertEqual(but_score["compound"], -0.4939)

    def test_multiple_buts_negate_after_the_first(self):
        line = "The food is great, but the service is horrible but"
        scores = self.si.polarity_scores(line)
        self.assertEqual(scores["compound"], -0.4939)
