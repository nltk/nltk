# Natural Language Toolkit: Ngram Association Measures
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Provides scoring functions for a number of association measures through a
generic, abstract implementation in L{NgramAssocMeasures}, and n-specific
L{BigramAssocMeasures} and L{TrigramAssocMeasures}.
"""

import math as _math
_log2 = lambda x: _math.log(x, 2.0)
_ln = _math.log

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

    @staticmethod
    def _marginals(*contingency):
        """Calculates values of contingency table marginals from its values."""
        raise NotImplementedError, ("The contingency table is not available"
                                    "in the general ngram case")

    @classmethod
    def _expected_values(cls, cont):
        """Calculates expected values for a contingency table."""
        n_all = sum(cont)
        bits = [1 << i for i in range(cls._n)]

        # For each contingency table cell
        for i in range(len(cont)):
            # Yield the expected value
            yield (_product(cont[i] + cont[i ^ j] for j in bits) /
                   float(n_all ** 2))

    @staticmethod
    def raw_freq(*marginals):
        """Scores ngrams by their frequency"""
        return float(marginals[NGRAM]) / marginals[TOTAL]

    @classmethod
    def student_t(cls, *marginals):
        """Scores ngrams using Student's t test with independence hypothesis
        for unigrams, as in Manning and Schutze 5.3.2.
        """
        return ((marginals[NGRAM] * marginals[TOTAL] -
                 _product(marginals[UNIGRAMS])) /
                (marginals[TOTAL] ** (cls._n - 1) *
                (marginals[NGRAM] + _SMALL) ** .5))

    @classmethod
    def chi_sq(cls, *marginals):
        """Scores ngrams using Pearson's chi-square as in Manning and Schutze
        5.3.3.
        """
        cont = cls._contingency(*marginals)
        exps = cls._expected_values(cont)
        return sum((obs - exp) ** 2 / (exp + _SMALL)
                   for obs, exp in zip(cont, exps))

    @staticmethod
    def mi_like(*marginals, **kwargs):
        """Scores ngrams using a variant of mutual information. The keyword
        argument power sets an exponent (default 3) for the numerator. No
        logarithm of the result is calculated.
        """
        return (marginals[NGRAM] ** kwargs.get('power', 3) /
                float(_product(marginals[UNIGRAMS])))

    @classmethod
    def pmi(cls, *marginals):
        """Scores ngrams by pointwise mutual information, as in Manning and
        Schutze 5.4.
        """
        return (_log2(marginals[NGRAM] * marginals[TOTAL] ** (cls._n - 1)) -
                _log2(_product(marginals[UNIGRAMS])))

    @classmethod
    def likelihood_ratio(cls, *marginals):
        """Scores ngrams using likelihood ratios as in Manning and Schutze 5.3.4.
        """
        cont = cls._contingency(*marginals)
        return (cls._n * 2 *
                sum(obs * _ln(float(obs) / (exp + _SMALL) + _SMALL)
                    for obs, exp in zip(cont, cls._expected_values(cont))))

    @classmethod
    def poisson_stirling(cls, *marginals):
        """Scores ngrams using the Poisson-Stirling measure."""
        exp = (_product(marginals[UNIGRAMS]) /
              float(marginals[TOTAL] ** (cls._n - 1)))
        return marginals[NGRAM] * (_log2(marginals[NGRAM] / exp) - 1)

    @classmethod
    def jaccard(cls, *marginals):
        """Scores ngrams using the Jaccard index."""
        cont = cls._contingency(*marginals)
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

    This may be shown with respect to a contingency table:
                w1    ~w1
             ------ ------
         w2 | n_ii | n_oi | = n_xi
             ------ ------
        ~w2 | n_io | n_oo |
             ------ ------
             = n_ix        TOTAL = n_xx
    """

    _n = 2

    @staticmethod
    def _contingency(n_ii, (n_ix, n_xi), n_xx):
        """Calculates values of a bigram contingency table from marginal values."""
        n_oi = n_xi - n_ii
        n_io = n_ix - n_ii
        return (n_ii, n_oi, n_io, n_xx - n_ii - n_oi - n_io)

    @staticmethod
    def _marginals(n_ii, n_oi, n_io, n_oo):
        """Calculates values of contingency table marginals from its values."""
        return (n_ii, (n_oi + n_ii, n_io + n_ii), n_oo + n_oi + n_io + n_ii)

    @staticmethod
    def _expected_values(cont):
        """Calculates expected values for a contingency table."""
        n_xx = sum(cont)
        # For each contingency table cell
        for i in range(4):
            yield (cont[i] + cont[i ^ 1]) * (cont[i] + cont[i ^ 2]) / float(n_xx)

    @classmethod
    def phi_sq(cls, *marginals):
        """Scores bigrams using phi-square, the square of the Pearson correlation
        coefficient.
        """
        n_ii, n_io, n_oi, n_oo = cls._contingency(*marginals)

        return (float((n_ii*n_oo - n_io*n_oi)**2) /
                ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))

    @classmethod
    def chi_sq(cls, n_ii, (n_ix, n_xi), n_xx):
        """Scores bigrams using chi-square, i.e. phi-sq multiplied by the number
        of bigrams, as in Manning and Schutze 5.3.3.
        """
        return n_xx * cls.phi_sq(n_ii, (n_ix, n_xi), n_xx)

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

    @staticmethod
    def _marginals(*contingency):
        """Calculates values of contingency table marginals from its values."""
        n_iii, n_oii, n_ioi, n_ooi, n_iio, n_oio, n_ioo, n_ooo = contingency
        return (n_iii,
                (n_iii + n_iio, n_iii + n_ioi, n_iii + n_oii),
                (n_iii + n_ioi + n_iio + n_ioo,
                 n_iii + n_oii + n_iio + n_oio,
                 n_iii + n_oii + n_ioi + n_ooi),
                sum(contingency))


class ContingencyMeasures(object):
    """Wraps NgramAssocMeasures classes such that the arguments of association
    measures are contingency table values rather than marginals.
    """

    def __init__(self, measures):
        """Constructs a ContingencyMeasures given a NgramAssocMeasures class"""
        self.__class__.__name__ = 'Contingency' + measures.__class__.__name__
        for k in dir(measures):
            if k.startswith('__'):
                continue
            v = getattr(measures, k)
            if not k.startswith('_'):
                v = self._make_contingency_fn(measures, v)
            setattr(self, k, v)

    @staticmethod
    def _make_contingency_fn(measures, old_fn):
        """From an association measure function, produces a new function which
        accepts contingency table values as its arguments.
        """
        def res(*contingency):
            return old_fn(*measures._marginals(*contingency))
        res.__doc__ = old_fn.__doc__
        res.__name__ = old_fn.__name__
        return res

