# Natural Language Toolkit: Bigram Assoc Measures
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import math as _math
_log = lambda x: _math.log(x, 2.0)

_product = lambda s: reduce(lambda x, y: x * y, s)

_SMALL = 1e-20


### Indices to marginals arguments:

NGRAM = 0
"""Marginals index for the ngram count"""

UNIGRAMS = -2
"""Marginals index for a tuple of each unigram count"""

TOTAL = -1
"""Marginals index for the number of words in the data"""


class NgramAssocMeasures(object):
    """
    An abstract class defining a collection of generic association measures.
    Each public method returns a score, taking the following arguments:
        score_fn(count_of_ngram,
                 (count_of_n-1gram_1, ..., count_of_n-1gram_j),
                 (count_of_n-2gram_1, ..., count_of_n-2gram_k),
                 ...,
                 (count_of_1gram_1, ..., count_of_1gram_n),
                 count_of_total_words)
    See L{BigramAssocMeasures} and L{TrigramAssocMeasures}

    Inheriting classes should define a property _n, and a method _contingency
    which calculates contingency values from marginals in order for all
    association measures defined here to be usable.
    """

    @staticmethod
    def _contingency(*marginals):
        """Calculates values of a contingency table from marginal values."""
        raise NotImplementedError, ("The contingency table is not available"
                                    "in the general ngram case")

    def _expected_values(self, cont):
        """Calculates expected values for a contingency table."""
        n_all = sum(cont)
        bits = [1 << i for i in range(self._n)]

        # For each contingency table cell
        for i in range(len(cont)):
            # Yield the expected value
            yield (_product(cont[i] + cont[i ^ j] for j in bits) /
                   float(n_all ** 2))

    @staticmethod
    def raw_freq(*marginals):
        """Scores ngrams by their frequency"""
        return float(marginals[NGRAM]) / marginals[TOTAL]

    class MILikeScorer(object):
        def __init__(self, power=3):
            self.power = power

        def __call__(self, *marginals):
            """Scores ngrams using a variant of mutual information"""
            return (marginals[NGRAM] ** self.power /
                    float(_product(marginals[UNIGRAMS])))

    mi_like = MILikeScorer()

    def pmi(self, *marginals):
        """Scores ngrams by pointwise mutual information, as in Manning and
        Schutze 5.4.
        """
        return (_log(marginals[NGRAM] * marginals[TOTAL] ** (self._n - 1)) -
                _log(_product(marginals[UNIGRAMS])))

    def student_t(self, *marginals):
        """Scores ngrams using Student's t test with independence hypothesis
        for unigrams, as in Manning and Schutze 5.3.2.
        """
        return (marginals[NGRAM] - _product(marginals[UNIGRAMS]) /
                (marginals[TOTAL] ** (self._n - 1) *
                (marginals[NGRAM] + _SMALL) ** .5))

    def chi_sq(self, *marginals):
        """Scores ngrams using Pearson's chi-square as in Manning and Schutze
        5.3.3.
        """
        cont = self._contingency(*marginals)
        exps = self._expected_values(cont)
        return sum((obs - exp) ** 2 / (exp + _SMALL)
                   for obs, exp in zip(cont, exps))

    def likelihood_ratio(self, *marginals):
        """Scores ngrams using likelihood ratios as in Manning and Schutze 5.3.4.
        """
        cont = self._contingency(*marginals)
        # Although probably obvious, I don't understand why this negation is needed
        return (-1 ** self._n * 2 *
                sum(obs * _log(float(obs) / (exp + _SMALL) + _SMALL)
                    for obs, exp in zip(cont, self._expected_values(cont))))

    def poisson_stirling(self, *marginals):
        """Scores ngrams using the Poisson-Stirling measure."""
        exp = (_product(marginals[UNIGRAMS]) /
              float(marginals[TOTAL] ** (self._n - 1)))
        return marginals[NGRAM] * (_log(marginals[NGRAM] / exp) - 1)

    def jaccard(self, *marginals):
        """Scores ngrams using the Jaccard index."""
        cont = self._contingency(*marginals)
        return float(cont[0]) / sum(cont[:-1])


class BigramAssocMeasures(NgramAssocMeasures):
    """
    A collection of trigram association measures. Each association measure
    is provided as a function with three arguments:
        bigram_score_fn(n_ii, (n_ix, n_xi), n_xx)
    The arguments constitute the marginals of a contingency table, counting
    the occurrences of particular events in a corpus. The letter i in the
    suffix refers to the appearance of the word in question, while x indicates
    the appearance of any word. Thus, for example:
    n_ii counts (w1, w2), i.e. the bigram being scored
    n_ix counts (w1, *)
    n_xi counts (*, w2)
    n_xx counts (*, *), i.e. any bigram
    """

    _n = 2

    @staticmethod
    def _contingency(n_ii, (n_ix, n_xi), n_xx):
        """Calculates values of a bigram contingency table from marginal values."""
        n_oi = n_xi - n_ii
        n_io = n_ix - n_ii
        return (n_ii, n_oi, n_io, n_xx - n_ii - n_oi - n_io)

    @staticmethod
    def _expected_values(cont):
        """Calculates expected values for a contingency table."""
        n_xx = sum(cont)
        # For each contingency table cell
        for i in range(4):
            yield (cont[i] + cont[i ^ 1]) * (cont[i] + cont[i ^ 2]) / float(n_xx)

    def phi_sq(self, *marginals):
        """Scores bigrams using phi-square, the square of the Pearson correlation
        coefficient.
        """
        n_ii, n_io, n_oi, n_oo = self._contingency(*marginals)

        return (float((n_ii*n_oo - n_io*n_oi)**2) /
                ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))

    def chi_sq(self, n_ii, (n_ix, n_xi), n_xx):
        """Scores bigrams using chi-square, i.e. phi-sq multiplied by the number
        of bigrams, as in Manning and Schutze 5.3.3.
        """
        return n_xx * self.phi_sq(n_ii, (n_ix, n_xi), n_xx)

    @staticmethod
    def dice(n_ii, (n_ix, n_xi), n_xx):
        """Scores bigrams using Dice's coefficient."""
        return 2 * float(n_ii) / (n_ix + n_xi)


class TrigramAssocMeasures(NgramAssocMeasures):
    """
    A collection of trigram association measures. Each association measure
    is provided as a function with four arguments:
        trigram_score_fn(n_iii,
                         (n_iix, n_ixi, n_xii),
                         (n_ixx, n_xix, n_xxi),
                         n_xxx)
    The arguments constitute the marginals of a contingency table, counting
    the occurrences of particular events in a corpus. The letter i in the
    suffix refers to the appearance of the word in question, while x indicates
    the appearance of any word. Thus, for example:
    n_iii counts (w1, w2, w3), i.e. the trigram being scored
    n_ixx counts (w1, *, *)
    n_xxx counts (*, *, *), i.e. any trigram
    """

    _n = 3

    @staticmethod
    def _contingency(n_iii,
                 (n_iix, n_ixi, n_xii),
                 (n_ixx, n_xix, n_xxi),
                 n_xxx):
        """Calculates values of a trigram contingency table (or cube) from marginal
        values.
        """
        n_oii = n_xii - n_iii
        n_ioi = n_ixi - n_iii
        n_iio = n_iix - n_iii
        n_ooi = n_xxi - n_iii - n_oii - n_ioi
        n_oio = n_xix - n_iii - n_oii - n_iio
        n_ioo = n_ixx - n_iii - n_ioi - n_iio
        n_ooo = n_xxx - n_iii - n_oii - n_ioi - n_iio - n_ooi - n_oio - n_ioo

        return (n_iii, n_oii, n_ioi, n_ooi,
                n_iio, n_oio, n_ioo, n_ooo)
