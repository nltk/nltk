# Natural Language Toolkit: Aligned Sentences
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import logging
from collections import defaultdict

from nltk.metrics import precision, recall

class AlignedSent(object):
    """
    Return an aligned sentence object, which encapsulates two sentences along with
    an ``Alignment`` between them.

        >>> from nltk.align import AlignedSent
        >>> algnsent = AlignedSent(['klein', 'ist', 'das', 'Haus'],
        ...     ['the', 'house', 'is', 'small'], '0-2 1-3 2-1 3-0')
        >>> algnsent.words
        ['klein', 'ist', 'das', 'Haus']
        >>> algnsent.mots
        ['the', 'house', 'is', 'small']
        >>> algnsent.alignment
        Alignment([(0, 2), (1, 3), (2, 1), (3, 0)])
        >>> algnsent.precision('0-2 1-3 2-1 3-3')
        0.75
        >>> from nltk.corpus import comtrans
        >>> print comtrans.aligned_sents()[54]
        <AlignedSent: 'Weshalb also sollten...' -> 'So why should EU arm...'>
        >>> print comtrans.aligned_sents()[54].alignment
        0-0 0-1 1-0 2-2 3-4 3-5 4-7 5-8 6-3 7-9 8-9 9-10 9-11 10-12 11-6 12-6 13-13

    :param words: source language words
    :type words: list(str)
    :param mots: target language words
    :type mots: list(str)
    :param alignment: the word-level alignments between the source
        and target language
    :type alignment: Alignment
    """

    def __init__(self, words = [], mots = [], alignment = '', \
                 encoding = 'latin-1'):
        self._words = words
        self._mots = mots
        self.alignment = alignment

    @property
    def words(self):
        return self._words

    @property
    def mots(self):
        return self._mots

    def _get_alignment(self):
        return self._alignment
    def _set_alignment(self, alignment):
        if not isinstance(alignment, Alignment):
            alignment = Alignment(alignment)
        self._check_align(alignment)
        self._alignment = alignment
    alignment = property(_get_alignment, _set_alignment)

    def _check_align(self, a):
        """
        Check whether the alignments are legal.

        :param a: alignment to be checked
        :raise IndexError: if alignment is out of sentence boundary
        :rtype: boolean
        """
        if not all([0 <= p[0] < len(self._words) for p in a]):
            raise IndexError("Alignment is outside boundary of words")
        if not all([0 <= p[1] < len(self._mots) for p in a]):
            raise IndexError("Alignment is outside boundary of mots")
        return True

    def __repr__(self):
        """
        Return a string representation for this ``AlignedSent``.

        :rtype: str
        """
        return "AlignedSent(%r, %r, %r)" % (self._words, self._mots, self._alignment)

    def __str__(self):
        """
        Return a human-readable string representation for this ``AlignedSent``.

        :rtype: str
        """
        source = " ".join(self._words)[:20] + "..."
        target = " ".join(self._mots)[:20] + "..."
        return "<AlignedSent: '%s' -> '%s'>" % (source, target)

    def invert(self):
        """
        Return the aligned sentence pair, reversing the directionality

        :rtype: AlignedSent
        """
        return AlignedSent(self._mots, self._words,
                               self._alignment.invert())

    def precision(self, reference):
        """
        Return the precision of an aligned sentence with respect to a
        "gold standard" reference ``AlignedSent``.

        :type reference: AlignedSent or Alignment
        :param reference: A "gold standard" reference aligned sentence.
        :rtype: float or None
        """
        # Get alignments in set of 2-tuples form
        # The "possible" precision is used since it doesn't penalize for finding
        # an alignment that was marked as "possible" (NAACL corpus)

        align = self.alignment
        if isinstance(reference, AlignedSent):
            possible = reference.alignment
        else:
            possible = Alignment(reference)

        return precision(possible, align)


    def recall(self, reference):
        """
        Return the recall of an aligned sentence with respect to a
        "gold standard" reference ``AlignedSent``.

        :type reference: AlignedSent or Alignment
        :param reference: A "gold standard" reference aligned sentence.
        :rtype: float or None
        """
        # Get alignments in set of 2-tuples form
        # The "sure" recall is used so we don't penalize for missing an
        # alignment that was only marked as "possible".

        align = self.alignment
        if isinstance(reference, AlignedSent):
            sure = reference.alignment
        else:
            sure  = Alignment(reference)

        # Call NLTKs existing functions for recall
        return recall(sure, align)


    def alignment_error_rate(self, reference, possible=None):
        """
        Return the Alignment Error Rate (AER) of an aligned sentence
        with respect to a "gold standard" reference ``AlignedSent``.

        Return an error rate between 0.0 (perfect alignment) and 1.0 (no
        alignment).

            >>> from nltk.align import AlignedSent
            >>> s = AlignedSent(["the", "cat"], ["le", "chat"], [(0, 0), (1, 1)])
            >>> s.alignment_error_rate(s)
            0.0

        :type reference: AlignedSent or Alignment
        :param reference: A "gold standard" reference aligned sentence.
        :type possible: AlignedSent or Alignment or None
        :param possible: A "gold standard" reference of possible alignments
            (defaults to *reference* if None)
        :rtype: float or None
        """
        # Get alignments in set of 2-tuples form
        align = self.alignment
        if isinstance(reference, AlignedSent):
            sure = reference.alignment
        else:
            sure = Alignment(reference)

        if possible is not None:
            # Set possible alignment
            if isinstance(possible, AlignedSent):
                possible = possible.alignment
            else:
                possible = Alignment(possible)
        else:
            # Possible alignment is just sure alignment
            possible = sure

        # Sanity check
        assert(sure.issubset(possible))

        # Return the Alignment Error Rate
        return (1.0 - float(len(align & sure) + len(align & possible)) /
                float(len(align) + len(sure)))


class Alignment(frozenset):
    """
    A storage class for representing alignment between two sequences, s1, s2.
    In general, an alignment is a set of tuples of the form (i, j, ...)
    representing an alignment between the i-th element of s1 and the
    j-th element of s2.  Tuples are extensible (they might contain
    additional data, such as a boolean to indicate sure vs possible alignments).

        >>> from nltk.align import Alignment
        >>> a = Alignment([(0, 0), (0, 1), (1, 2), (2, 2)])
        >>> a.invert()
        Alignment([(0, 0), (1, 0), (2, 1), (2, 2)])
        >>> print a.invert()
        0-0 1-0 2-1 2-2
        >>> a[0]
        [(0, 1), (0, 0)]
        >>> a.invert()[2]
        [(2, 1), (2, 2)]
        >>> b = Alignment([(0, 0), (0, 1)])
        >>> b.issubset(a)
        True
        >>> c = Alignment('0-0 0-1')
        >>> b == c
        True
    """

    def __new__(cls, string_or_pairs):
        if isinstance(string_or_pairs, basestring):
            string_or_pairs = [_giza2pair(p) for p in string_or_pairs.split()]
        self = frozenset.__new__(cls, string_or_pairs)
        if self == frozenset([]):
            self._len = 0
        else:
            self._len = max(p[0] for p in self)
        self._index = None
        return self

    def __getitem__(self, key):
        """
        Look up the alignments that map from a given index or slice.
        """
        if not self._index:
            self._build_index()
        return self._index.__getitem__(key)

    def invert(self):
        """
        Return an Alignment object, being the inverted mapping.
        """
        return Alignment(((p[1], p[0]) + p[2:]) for p in self)

    def range(self, positions=None):
        """
        Work out the range of the mapping from the given positions.
        If no positions are specified, compute the range of the entire mapping.
        """
        image = set()
        if not self._index:
            self._build_index()
        if not positions:
            positions = range(len(self._index))
        for p in positions:
            image.update(f for _,f in self._index[p])
        return sorted(image)

    def __repr__(self):
        """
        Produce a Giza-formatted string representing the alignment.
        """
        return "Alignment(%r)" % sorted(self)

    def __str__(self):
        """
        Produce a Giza-formatted string representing the alignment.
        """
        return " ".join("%d-%d" % p[:2] for p in sorted(self))

    def _build_index(self):
        """
        Build a list self._index such that self._index[i] is a list
        of the alignments originating from word i.
        """
        self._index = [[] for _ in range(self._len + 1)]
        for p in self:
            self._index[p[0]].append(p)


class IBMModel1(object):
    """
    This class implements the Expectation Maximization algorithm for
    IBM Model 1. The algorithm runs upon a sentence-aligned parallel
    corpus and generates word alignments in aligned sentence pairs.
    The process is divided into 2 stages:

    - Stage 1: Calculates word-to-word translation probabilities by collecting
      evidence of a English word being the translation of a foreign word from
      the parallel corpus.
    - Stage 2: Generates updated word alignments for the sentence pairs, based
      on the translation probabilities from Stage 1.

        >>> corpus = [AlignedSent(['the', 'house'], ['das', 'Haus']),
        ...           AlignedSent(['the', 'book'], ['das', 'Buch']),
        ...           AlignedSent(['a', 'book'], ['ein', 'Buch'])]
        >>> ibm1 = IBMModel1(corpus)
        >>> print "%.1f" % ibm1.probabilities['book', 'Buch']
        1.0
        >>> print "%.1f" % ibm1.probabilities['book', 'das']
        0.0
        >>> print "%.1f" % ibm1.probabilities['book', None]
        0.5

    :param aligned_sents: The parallel text ``corpus.Iterable`` containing
        AlignedSent instances of aligned sentence pairs from the corpus.
    :type aligned_sents: list(AlignedSent)
    :param convergent_threshold: The threshold value of convergence. An
        entry is considered converged if the delta from ``old_t`` to ``new_t``
        is less than this value. The algorithm terminates when all entries
        are converged. This parameter is optional, default is 0.01
    :type convergent_threshold: float
    """

    def __init__(self, aligned_sents, convergent_threshold=1e-2, debug=False):
        self.aligned_sents = aligned_sents
        self.convergent_threshold = convergent_threshold
        # Dictionary of translation probabilities t(e,f).
        self.probabilities = None
        self._train()

    def _train(self):
        """
        Perform Expectation Maximization training to learn
        word-to-word translation probabilities.
        """
        logging.debug("Starting training")

        # Collect up sets of all English and foreign words
        english_words = set()
        foreign_words = set()
        for aligned_sent in self.aligned_sents:
            english_words.update(aligned_sent.words)
            foreign_words.update(aligned_sent.mots)
        # add the NULL token to the foreign word set.
        foreign_words.add(None)
        num_probs = len(english_words) * len(foreign_words)

        # Initialise t(e|f) uniformly
        default_prob = 1.0 / len(english_words)
        t = defaultdict(lambda: default_prob)

        convergent_threshold = self.convergent_threshold
        globally_converged = False
        iteration_count = 0
        while not globally_converged:
            # count(e|f)
            count = defaultdict(float)
            # total(f)
            total = defaultdict(float)

            for aligned_sent in self.aligned_sents:
                s_total = {}
                # Compute normalization
                for e_w in aligned_sent.words:
                    s_total[e_w] = 0.0
                    for f_w in aligned_sent.mots+[None]:
                        s_total[e_w] += t[e_w, f_w]

                # Collect counts
                for e_w in aligned_sent.words:
                    for f_w in aligned_sent.mots+[None]:
                        cnt = t[e_w, f_w] / s_total[e_w]
                        count[e_w, f_w] += cnt
                        total[f_w] += cnt

            # Estimate probabilities
            num_converged = 0
            for f_w in foreign_words:
                for e_w in english_words:
                    new_prob = count[e_w, f_w] / total[f_w]
                    delta = abs(t[e_w, f_w] - new_prob)
                    if delta < convergent_threshold:
                        num_converged += 1
                    t[e_w, f_w] = new_prob

            # Have we converged
            iteration_count += 1
            if num_converged == num_probs:
                globally_converged = True
            logging.debug("%d/%d (%.2f%%) converged" %
                          (num_converged, num_probs, 100.0*num_converged/num_probs))

        self.probabilities = dict(t)

    def aligned(self):
        """
        Return a list of AlignedSents with Alignments calculated using
        IBM-Model 1.
        """

        if self.probabilities is None:
            raise ValueError("No probabilities calculated")

        aligned = []
        # Alignment Learning from t(e|f)
        for aligned_sent in self.aligned_sents:
            alignment = []

            # for every English word
            for j, e_w in enumerate(aligned_sent.words):
                # find the French word that gives maximized t(e|f)
                # NULL token is the initial candidate
                f_max = (self.probabilities[e_w, None], None)
                for i, f_w in enumerate(aligned_sent.mots):
                    f_max = max(f_max, (self.probabilities[e_w, f_w], i))

                # only output alignment with non-NULL mapping
                if f_max[1] is not None:
                    alignment.append((j, f_max[1]))

            # substitute the alignment of AlignedSent with the yielded one
            aligned.append(AlignedSent(aligned_sent.words,
                    aligned_sent.mots,  alignment))

        return aligned


def _giza2pair(pair_string):
    i, j = pair_string.split("-")
    return int(i), int(j)

def _naacl2pair(pair_string):
    i, j, p = pair_string.split("-")
    return int(i), int(j)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
