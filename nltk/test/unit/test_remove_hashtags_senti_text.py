"""
Tests for nltk.sentiment.vader.remove_hashtag
"""

import unittest

from nltk.sentiment import SentimentIntensityAnalyzer


class TestRemoveHashtag(unittest.TestCase):
    def setUp(self):
        self.sentiment_analyser = SentimentIntensityAnalyzer()

    def test_remove_hashtag_multiple(self):
        """
        Test against multiple hashtags
        """
        case = "Strings with hashtag ###stupid ##useless ##BAD"
        expected = {"neg": 0.777, "neu": 0.223, "pos": 0.0, "compound": -0.8868}
        assert self.sentiment_analyser.polarity_scores(case) == expected

    def test_remove_hashtag_space(self):
        """
        Test against hashtag with spaces
        """
        case = "I feel very # happy # today"
        expected = {"neg": 0.0, "neu": 0.429, "pos": 0.571, "compound": 0.6115}
        assert self.sentiment_analyser.polarity_scores(case) == expected

    def test_remove_hashtag_postfix(self):
        """
        Test hashtags that comes after the text
        """
        case = "I feel very # happy# today#"
        expected = {"neg": 0.0, "neu": 0.429, "pos": 0.571, "compound": 0.6115}
        assert self.sentiment_analyser.polarity_scores(case) == expected

    def test_remove_hashtag_infix(self):
        """
        Test hashtags that comes in the middle of the text
        """
        case = "Strings with hashtag stup#id useless BA#D"
        expected = {"neg": 0.777, "neu": 0.223, "pos": 0.0, "compound": -0.8868}
        assert self.sentiment_analyser.polarity_scores(case) == expected
