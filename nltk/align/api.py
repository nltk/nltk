# Natural Language Toolkit: Aligned Sentences
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function, unicode_literals

from nltk.compat import python_2_unicode_compatible, string_types
from nltk.metrics import precision, recall

@python_2_unicode_compatible
class AlignedSent(object):
    """
    Return an aligned sentence object, which encapsulates two sentences
    along with an ``Alignment`` between them.

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
        >>> print(comtrans.aligned_sents()[54])
        <AlignedSent: 'Weshalb also sollten...' -> 'So why should EU arm...'>
        >>> print(comtrans.aligned_sents()[54].alignment)
        0-0 0-1 1-0 2-2 3-4 3-5 4-7 5-8 6-3 7-9 8-9 9-10 9-11 10-12 11-6 12-6 13-13

    :param words: source language words
    :type words: list(str)
    :param mots: target language words
    :type mots: list(str)
    :param alignment: the word-level alignments between the source
        and target language
    :type alignment: Alignment
    """

    def __init__(self, words=[], mots=[], alignment='', encoding='utf8'):
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
        if not all(0 <= p[0] < len(self._words) for p in a):
            raise IndexError("Alignment is outside boundary of words")
        if not all(0 <= p[1] < len(self._mots) for p in a):
            raise IndexError("Alignment is outside boundary of mots")
        return True

    def __repr__(self):
        """
        Return a string representation for this ``AlignedSent``.

        :rtype: str
        """
        words = "[%s]" % (", ".join("'%s'" % w for w in self._words))
        mots = "[%s]" % (", ".join("'%s'" % w for w in self._mots))

        return "AlignedSent(%s, %s, %r)" % (words, mots, self._alignment)

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


@python_2_unicode_compatible
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
        >>> print(a.invert())
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
        if isinstance(string_or_pairs, string_types):
            string_or_pairs = [_giza2pair(p) for p in string_or_pairs.split()]
        self = frozenset.__new__(cls, string_or_pairs)
        self._len = (max(p[0] for p in self) if self != frozenset([]) else 0)
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
            positions = list(range(len(self._index)))
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


def _giza2pair(pair_string):
    i, j = pair_string.split("-")
    return int(i), int(j)

def _naacl2pair(pair_string):
    i, j, p = pair_string.split("-")
    return int(i), int(j)

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
