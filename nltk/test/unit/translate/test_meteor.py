import unittest

from nltk.translate.meteor_score import meteor_score


class TestMETEOR(unittest.TestCase):
    def test_preprocess(self):
        # Using lists instead of strings specifically to demonstrate use of `preprocess`.
        reference = [["this", "is", "a", "test"], ["this", "is" "test"]]
        candidate = ["this", "is", "a", "test"]

        # no `preprocess` argument
        self.assertRaises(TypeError, meteor_score, reference, candidate)

        # with `preprocess` argument
        score = meteor_score(reference, candidate, preprocess=lambda x: " ".join(x))
        assert score == 0.9921875
