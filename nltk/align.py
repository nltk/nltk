# Natural Language Toolkit: Aligned Sentences
#
# Copyright (C) 2001-2011 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import logging

import nltk.metrics
from nltk.util import defaultdict

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

#    @alignment.setter Requires Python 2.6?
    def alignment(self, alignment):
        if not isinstance(alignment, Alignment):
            alignment = Alignment(alignment)
        self._check_align(alignment)
        self._alignment = alignment

    def _check_align(self, a):
        """
        @param a: alignment to be checked
        @raise IndexError: if alignment is out of sentence boundary
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

        @type reference: C{AlignedSent} or C{Alignment}
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

        @type reference: C{AlignedSent} or C{Alignment}
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


    def alignment_error_rate(self, reference, possible=None):
        """Calculates the Alignment Error Rate (AER) of an aligned sentence 
        with respect to a "gold standard" reference C{AlignedSent}.

        Return an error rate between 0.0 (perfect alignment) and 1.0 (no 
        alignment).

        @type reference: C{AlignedSent} or C{Alignment}
        @param reference: A "gold standard" reference aligned sentence.
        @type possible: C{AlignedSent} or C{Alignment} or C{None}
        @param possible: A "gold standard" reference of possible alignments
            (defaults to I{reference} if C{None})
        @rtype: C{float} or C{None}
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


class EMIBMModel1(object):
    '''
    This class contains implementations of the Expectation Maximization
    algorithm for IBM Model 1. The algorithm runs upon a sentence-aligned 
    parallel corpus and generates word alignments in aligned sentence pairs.

    The process is divided into 2 main stages.
    Stage 1: Studies word-to-word translation probabilities by collecting
    evidence of a English word been the translation of a foreign word from
    the parallel corpus.

    Stage 2: Based on the translation probabilities from Stage 1, generates 
    word alignments for aligned sentence pairs.
    '''

    def __init__(self, aligned_sents, convergent_threshold=1e-2, debug=False):
        '''
        Initialize a new C{EMIBMModel1}.

        @param aligned_sents: The parallel text corpus.Iteratable containing 
            AlignedSent instances of aligned sentence pairs from the corpus.
        @type aligned_sents: C{list} of L{AlignedSent} objects
        @param convergent_threshold: The threshold value of convergence. An 
            entry is considered converged if the delta from old_t to new_t
            is less than this value. The algorithm terminates when all entries
            are converged. This parameter is optional, default is 0.01
        @type convergent_threshold: C{float}
        '''
        self.aligned_sents = aligned_sents
        self.convergent_threshold = convergent_threshold
        # Dictionary of translation probabilities t(e,f).
        self.probabilities = None

    def train(self):
        '''
        The train() function implements Expectation Maximization training
        stage that learns word-to-word translation probabilities.

        @return: Number of iterations taken to converge
        '''

        # Collect up sets of all English and foreign words
        english_words = set()
        foreign_words = set()
        for aligned_sent in self.aligned_sents:
            english_words.update(aligned_sent.words)
            foreign_words.update(aligned_sent.mots)
        # add the NULL token to the foreign word set.
        foreign_words.add(None)
        num_probs = len(english_words)*len(foreign_words)

        # Initialise t(e|f) uniformly
        t = defaultdict(lambda: float(1)/len(english_words))
        s_total = defaultdict(float)
        for e in english_words:
            for f in foreign_words:
                z = t[e,f]

        globally_converged = False
        iteration_count = 0
        while not globally_converged:
            # count(e|f)
            count = defaultdict(float)
            # total(f)
            total = defaultdict(float)

            for aligned_sent in self.aligned_sents:
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
                    if delta < self.convergent_threshold:
                        num_converged += 1
                    t[e_w, f_w] = new_prob

            # Have we converged
            iteration_count += 1
            if num_converged == num_probs:
                globally_converged = True
            logging.debug("%d/%d (%.2f%%) converged"%(
                    num_converged, num_probs, 100.0*num_converged/num_probs))

        self.probabilities = dict(t)
        return iteration_count

    def aligned(self):
        '''
        Returns a list of AlignedSents with Alignments calculated using 
        IBM-Model 1.
        '''
        if self.probablities is None:
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

