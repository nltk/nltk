import unittest

from nltk.collocations import TrigramCollocationFinder
from nltk.metrics import (
    BigramAssocMeasures,
    QuadgramAssocMeasures,
    TrigramAssocMeasures,
)

## Test the likelihood ratio metric

_DELTA = 1e-8


class TestLikelihoodRatio(unittest.TestCase):
    def test_lr_bigram(self):
        self.assertAlmostEqual(
            BigramAssocMeasures.likelihood_ratio(2, (4, 4), 20),
            2.4142743368419755,
            delta=_DELTA,
        )
        self.assertAlmostEqual(
            BigramAssocMeasures.likelihood_ratio(1, (1, 1), 1), 0.0, delta=_DELTA
        )
        self.assertRaisesRegex(
            ValueError,
            "contingency table contains negative counts",
            BigramAssocMeasures.likelihood_ratio,
            *(0, (2, 2), 2),
        )

    def test_lr_trigram(self):
        self.assertAlmostEqual(
            TrigramAssocMeasures.likelihood_ratio(1, (1, 1, 1), (1, 1, 1), 2),
            5.545177444479562,
            delta=_DELTA,
        )
        self.assertAlmostEqual(
            TrigramAssocMeasures.likelihood_ratio(1, (1, 1, 1), (1, 1, 1), 1),
            0.0,
            delta=_DELTA,
        )
        self.assertRaisesRegex(
            ValueError,
            "contingency table contains negative counts",
            TrigramAssocMeasures.likelihood_ratio,
            *(1, (1, 1, 2), (1, 1, 2), 2),
        )

    def test_lr_quadgram(self):
        self.assertAlmostEqual(
            QuadgramAssocMeasures.likelihood_ratio(
                1, (1, 1, 1, 1), (1, 1, 1, 1, 1, 1), (1, 1, 1, 1), 2
            ),
            8.317766166719343,
            delta=_DELTA,
        )
        self.assertAlmostEqual(
            QuadgramAssocMeasures.likelihood_ratio(
                1, (1, 1, 1, 1), (1, 1, 1, 1, 1, 1), (1, 1, 1, 1), 1
            ),
            0.0,
            delta=_DELTA,
        )
        self.assertRaisesRegex(
            ValueError,
            "contingency table contains negative counts",
            QuadgramAssocMeasures.likelihood_ratio,
            *(1, (1, 1, 1, 1), (1, 1, 1, 1, 1, 2), (1, 1, 1, 1), 1),
        )

    def test_lr_trigram_small_sample(self):
        finder = TrigramCollocationFinder.from_words(["borrower"] * 6 + ["page"])
        finder.apply_freq_filter(3)
        with self.assertRaisesRegex(
            ValueError, "contingency table contains negative counts"
        ):
            finder.nbest(TrigramAssocMeasures.likelihood_ratio, 8)
