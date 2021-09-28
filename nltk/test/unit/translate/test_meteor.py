import unittest

from nltk.translate.meteor_score import meteor_score


class TestMETEOR(unittest.TestCase):
    def test_meteor(self):
        reference = [["this", "is", "a", "test"], ["this", "is" "test"]]
        candidate = ["THIS", "Is", "a", "tEST"]

        score = meteor_score(reference, candidate, preprocess=str.lower)
        assert score == 0.9921875
