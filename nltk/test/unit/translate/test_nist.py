"""
Tests for NIST translation evaluation metric
"""

import io
import unittest

from nltk.data import find, open_datafile
from nltk.translate.nist_score import corpus_nist, sentence_nist

# The sentences from the sentence_nist doctest. The expected scores below were
# computed with mteval-v13a.pl on the same whitespace tokens, with the -c flag
# so that the case is preserved.
HYPOTHESIS1 = (
    "It is a guide to action which ensures that the military always obeys the "
    "commands of the party"
).split()
HYPOTHESIS2 = (
    "It is to insure the troops forever hearing the activity guidebook that party "
    "direct"
).split()
REFERENCE1 = (
    "It is a guide to action that ensures that the military will forever heed "
    "Party commands"
).split()
REFERENCE2 = (
    "It is the guiding principle which guarantees the military forces always "
    "being under the command of the Party"
).split()
REFERENCE3 = (
    "It is the practical guide for the army always to heed the directions of the "
    "party"
).split()


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

    def test_single_reference_matches_mteval(self):
        self.assertAlmostEqual(
            sentence_nist([REFERENCE1], HYPOTHESIS1, n=1), 2.388888888889, places=8
        )
        self.assertAlmostEqual(
            sentence_nist([REFERENCE1], HYPOTHESIS1), 2.447712418300, places=8
        )
        self.assertAlmostEqual(
            sentence_nist([REFERENCE1], HYPOTHESIS2), 1.523880196056, places=8
        )

    def test_multiple_references_match_mteval(self):
        references = [REFERENCE1, REFERENCE2, REFERENCE3]
        self.assertAlmostEqual(
            sentence_nist(references, HYPOTHESIS1, n=1), 4.292547512225, places=8
        )
        self.assertAlmostEqual(
            sentence_nist(references, HYPOTHESIS1, n=2), 4.876360012514, places=8
        )
        self.assertAlmostEqual(
            sentence_nist(references, HYPOTHESIS1), 5.037920168830, places=8
        )
        self.assertAlmostEqual(
            sentence_nist(references, HYPOTHESIS2), 2.113874560032, places=8
        )

    def test_corpus_multiple_references_matches_mteval(self):
        list_of_references = [[REFERENCE1, REFERENCE2, REFERENCE3]] * 2
        hypotheses = [HYPOTHESIS1, HYPOTHESIS2]
        self.assertAlmostEqual(
            corpus_nist(list_of_references, hypotheses, n=1), 3.441575964369, places=8
        )
        self.assertAlmostEqual(
            corpus_nist(list_of_references, hypotheses, n=2), 3.770086809712, places=8
        )
        self.assertAlmostEqual(
            corpus_nist(list_of_references, hypotheses), 3.861760533218, places=8
        )

    def test_ngrams_match_any_reference(self):
        # Every hypothesis unigram appears in one of the two references, so all
        # four of them count. Each of A, B, C and D occurs once in the eight
        # reference words and carries 3 bits of information, so the unigram
        # precision is 12 / 4. The bigrams A B and C D carry no information
        # because A is always followed by B and C by D.
        hypothesis = "A B C D".split()
        references = ["A B x y".split(), "x y C D".split()]
        self.assertAlmostEqual(sentence_nist(references, hypothesis, n=4), 3.0)
        # With only the first reference, A and B are the only matches.
        self.assertAlmostEqual(sentence_nist(references[:1], hypothesis, n=4), 1.0)

    def test_length_penalty_uses_average_reference_length(self):
        hypothesis = "the quick brown fox jumps over the lazy dog".split()
        same = list(hypothesis)
        longer = (
            "a completely different sentence that shares nothing with the "
            "hypothesis and keeps going for a while longer"
        ).split()
        assert len(hypothesis) == 9 and len(longer) == 17
        # The hypothesis is one of the references, but the references are 13
        # words long on average, so the length penalty for 9 / 13 applies.
        self.assertAlmostEqual(
            sentence_nist([same, longer], hypothesis, n=1), 2.458743696739, places=8
        )
        self.assertAlmostEqual(
            sentence_nist([same, longer], hypothesis), 2.682801548802, places=8
        )
        # With the single matching reference there is no length penalty.
        self.assertAlmostEqual(
            sentence_nist([same], hypothesis), 3.197702779220, places=8
        )
