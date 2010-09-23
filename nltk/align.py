# Natural Language Toolkit: Aligned Sentences
#
# Copyright (C) 2001-2010 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import nltk.metrics

class AlignedSent(object):
    """
    Aligned sentence object.  Encapsulates two sentences along with
    an C{Alignment} between them.
    """
    
    def __init__(self, words = [], mots = [], alignment = '', \
                 encoding = 'latin-1'):
        """
        Initialize a new C{AlignedSent}.
        
        @param words: source language words
        @type words: C{list} of C{str}
        @param mots: target language words
        @type mots: C{list} of C{str}
        @param alignment: the word-level alignments between the source
            and target language
        @type alignment: C{Alignment}
        """
        if not isinstance(alignment, Alignment):
            alignment = Alignment(alignment)
        self._words = words
        self._mots = mots
        self._check_align(alignment)
        self._alignment = alignment

    @property
    def words(self):
        return self._words

    @property
    def mots(self):
        return self._mots

    @property
    def alignment(self):
        return self._alignment

    @alignment.setter
    def alignment(self, alignment):
        if not isinstance(alignment, Alignment):
            alignment = Alignment(alignment)
        self._check_align(alignment)
        self._alignment = alignment

    def _check_align(self, a):
        """
        @param a: alignment to be checked
        @raise: IndexError if alignment is out of sentence boundary
        @return: True if passed alignment check
        @rtype: boolean
        """
        if not all([0 <= p[0] < len(self._words) for p in a]):
            raise IndexError("Alignment is outside boundary of words")
        if not all([0 <= p[1] < len(self._mots) for p in a]):
            raise IndexError("Alignment is outside boundary of mots")
        return True

    def __repr__(self):
        """
        @return: A string representation for this C{AlignedSent}.
        @rtype: C{string}
        """
        return "AlignedSent(%r, %r, %r)" % (self._words, self._mots, self._alignment)

    def __str__(self):
        """
        @return: A string representation for this C{AlignedSent}.
        @rtype: C{string}
        """
        source = " ".join(self._words)[:20] + "..."
        target = " ".join(self._mots)[:20] + "..."
        return "<AlignedSent: '%s' -> '%s'>" % (source, target)

    def invert(self):
        """ 
        @return: the invert object
        @rtype: AlignedSent
        """
        return AlignedSent(self._mots, self._words,
                               self._alignment.invert())

    def precision(self, reference):
        """Calculates the precision of an aligned sentence with respect to a 
        "gold standard" reference C{AlignedSent}.

        The "possible" precision is used since it doesn't penalise for finding
        an alignment that was marked as "possible".

        @type reference: C{AlignedSent} or C{set}
        @param reference: A "gold standard" reference aligned sentence.
        @rtype: C{float} or C{None}
        """
        # Get alignments in set of 2-tuples form
        align = self.alignment
        if isinstance(reference, AlignedSent):
            possible = reference.alignment
        else:
            possible = Alignment(reference)

        # Call NLTKs existing functions for precision
        return nltk.metrics.scores.precision(possible, align)


    def recall(self, reference):
        """Calculates the recall of an aligned sentence with respect to a 
        "gold standard" reference C{AlignedSent}.

        The "sure" recall is used so we don't penalise for missing an 
        alignment that was only marked as "possible".

        @type reference: C{AlignedSent} or C{set}
        @param reference: A "gold standard" reference aligned sentence.
        @rtype: C{float} or C{None}
        """
        # Get alignments in set of 2-tuples form
        align = self.alignment
        if isinstance(reference, AlignedSent):
            sure = reference.alignment
        else:
            sure  = Alignment(reference)

        # Call NLTKs existing functions for recall
        return nltk.metrics.scores.recall(sure, align)


    def alignment_error_rate(self, reference):
        """Calculates the Alignment Error Rate (AER) of an aligned sentence 
        with respect to a "gold standard" reference C{AlignedSent}.

        Return an error rate between 0.0 (perfect alignment) and 1.0 (no 
        alignment).

        @type reference: C{AlignedSent} or C{set} or
        @param reference: A "gold standard" reference aligned sentence.
        @rtype: C{float} or C{None}
        """
        # Get alignments in set of 2-tuples form
        align = self.alignment
        if isinstance(reference, AlignedSent):
            sure = reference.alignment
            possible = reference.alignment
        else:
            sure = Alignment(reference)
            possible = Alignment(reference)

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


def _giza2pair(pair_string):
    i, j = pair_string.split("-")
    return int(i), int(j)

def _naacl2pair(pair_string):
    i, j, p = pair_string.split("-")
    return int(i), int(j)

