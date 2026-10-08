"""
Tests for NIST translation evaluation metric
"""

import io
import unittest
import warnings

from nltk.data import find, open_datafile
from nltk.translate.nist_score import corpus_nist


class TestNIST(unittest.TestCase):
    def test_sentence_nist(self):
        ref_file = find("models/wmt15_eval/ref.ru")
        hyp_file = find("models/wmt15_eval/google.ru")
        mteval_output_file = find("models/wmt15_eval/mteval-13a.output")

        # Reads the NIST scores from the `mteval-13a.output` file.
        # The order of the list corresponds to the order of the ngrams.
        with open_datafile(mteval_output_file) as mteval_fin:
            # The numbers are located in the last 4th line of the file.
            # The first and 2nd item in the list are the score and system names.
            mteval_nist_scores = map(float, mteval_fin.readlines()[-4].split()[1:-1])

        with open_datafile(ref_file, encoding="utf8") as ref_fin:
            with open_datafile(hyp_file, encoding="utf8") as hyp_fin:
                # Whitespace tokenize the file.
                # Note: split() automatically strip().
                hypotheses = list(map(lambda x: x.split(), hyp_fin))
                # Note that the corpus_bleu input is list of list of references.
                references = list(map(lambda x: [x.split()], ref_fin))
                # Without smoothing.
                for i, mteval_nist in zip(range(1, 10), mteval_nist_scores):
                    nltk_nist = corpus_nist(references, hypotheses, i)
                    # Check that the NIST scores difference is less than 0.5
                    assert abs(mteval_nist - nltk_nist) < 0.05

    def test_too_big_n(self):
        # hypothesis with length 18
        hypothesis = "It is a guide to action which ensures that the military always obeys the commands of the party".split()

        references = [
            "It is the guide to action that ensures that the military will forever heed Party commands".split(),
            "It is the guding principle which guarantees the military forces always being under the command of the Party".split(),
            "It is the practical guide for the army always to heed the directions of the party".split(),
        ]
        # normal case, should be greater than 0.0
        nist_score = corpus_nist([references], [hypothesis])
        assert nist_score > 0.0
        # too big n(20), should warn with warnings.warn
        # Note: the result of corpus_nist is not tested here because it is not stable when n is too large.
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nist_score = corpus_nist([references], [hypothesis], n=20)
            assert len(w) >= 1
            has_correct_warning = False
            for warning in w:
                if (
                    "Default smoothing function will be applied to avoid zero division"
                    in str(warning.message)
                ):
                    has_correct_warning = True
                    break
            assert has_correct_warning
