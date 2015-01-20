# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 2
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__  import division
from collections import defaultdict
from nltk.align  import AlignedSent
from nltk.corpus import comtrans
from nltk.align.ibm1 import IBMModel1

class IBMModel2(object):
    """
    This class implements the algorithm of Expectation Maximization for 
    the IBM Model 2. 

    Step 1 - Run a number of iterations of IBM Model 1 and get the initial
             distribution of translation probability. 

    Step 2 - Collect the evidence of an English word being translated by a 
             foreign language word.

    Step 3 - Estimate the probability of translation and alignment according 
             to the evidence from Step 2. 

    >>> bitexts = comtrans.aligned_sents()[:100]
    >>> ibm = IBMModel2(bitexts, 5)
    >>> aligned_sent = ibm.align(bitexts[0])
    >>> aligned_sent.words
    ['Wiederaufnahme', 'der', 'Sitzungsperiode']
    >>> aligned_sent.mots
    ['Resumption', 'of', 'the', 'session']
    >>> aligned_sent.alignment
    Alignment([(0, 0), (1, 2), (2, 3)])
    >>> bitexts[0].precision(aligned_sent)
    0.75
    >>> bitexts[0].recall(aligned_sent)
    1.0
    >>> bitexts[0].alignment_error_rate(aligned_sent)
    0.1428571428571429

    """
    def __init__(self, align_sents, num_iter):
        self.probabilities, self.alignments = self.train(align_sents, num_iter)

    def train(self, align_sents, num_iter):
        """
        Return the translation and alignment probability distributions
        trained by the Expectation Maximization algorithm for IBM Model 2. 

        Arguments:
        align_sents   -- A list contains some sentence pairs.
        num_iter     -- The number of iterations.

        Returns:
        t_ef         -- A distribution of translation probabilities.
        align        -- A distribution of alignment probabilities.
        """

        # Get initial translation probability distribution
        # from a few iterations of Model 1 training.
        ibm1 = IBMModel1(align_sents, 10)
        t_ef = ibm1.probabilities

        # Vocabulary of each language
        fr_vocab = set()
        en_vocab = set()
        for alignSent in align_sents:
            en_vocab.update(alignSent.words)
            fr_vocab.update(alignSent.mots)
        fr_vocab.add(None)

        align = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: float))))

        # Initialize the distribution of alignment probability,
        # a(i|j,l_e, l_f) = 1/(l_f + 1)
        for alignSent in align_sents:
            en_set = alignSent.words
            fr_set = [None] + alignSent.mots
            l_f = len(fr_set) - 1
            l_e = len(en_set)
            initial_value = 1 / (l_f + 1)
            for i in range(0, l_f+1):
                for j in range(1, l_e+1):
                    align[i][j][l_e][l_f] = initial_value


        for i in range(0, num_iter):
            count_ef = defaultdict(lambda: defaultdict(float))
            total_f = defaultdict(float)

            count_align = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
            total_align = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0)))

            total_e = defaultdict(float)

            for alignSent in align_sents:
                en_set = alignSent.words
                fr_set = [None] + alignSent.mots
                l_f = len(fr_set) - 1
                l_e = len(en_set)

                # compute normalization
                for j in range(1, l_e+1):
                    en_word = en_set[j-1]
                    total_e[en_word] = 0
                    for i in range(0, l_f+1):
                        total_e[en_word] += t_ef[en_word][fr_set[i]] * align[i][j][l_e][l_f]

                # collect counts
                for j in range(1, l_e+1):
                    en_word = en_set[j-1]
                    for i in range(0, l_f+1):
                        fr_word = fr_set[i]
                        c = t_ef[en_word][fr_word] * align[i][j][l_e][l_f] / total_e[en_word]
                        count_ef[en_word][fr_word] += c
                        total_f[fr_word] += c
                        count_align[i][j][l_e][l_f] += c
                        total_align[j][l_e][l_f] += c

            # estimate probabilities
            t_ef = defaultdict(lambda: defaultdict(lambda: 0.0))
            align = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))

            # Smoothing the counts for alignments
            for alignSent in align_sents:
                en_set = alignSent.words
                fr_set = [None] + alignSent.mots
                l_f = len(fr_set) - 1
                l_e = len(en_set)

                laplace = 1.0
                for i in range(0, l_f+1):
                    for j in range(1, l_e+1):
                        value = count_align[i][j][l_e][l_f]
                        if 0 < value < laplace:
                            laplace = value

                laplace *= 0.5 
                for i in range(0, l_f+1):
                    for j in range(1, l_e+1):
                        count_align[i][j][l_e][l_f] += laplace

                initial_value = laplace * l_e
                for j in range(1, l_e+1):
                    total_align[j][l_e][l_f] += initial_value
            
            # Estimate the new lexical translation probabilities
            for f in fr_vocab:
                for e in en_vocab:
                    t_ef[e][f] = count_ef[e][f] / total_f[f]

            # Estimate the new alignment probabilities
            for alignSent in align_sents:
                en_set = alignSent.words
                fr_set = [None] + alignSent.mots
                l_f = len(fr_set) - 1
                l_e = len(en_set)
                for i in range(0, l_f+1):
                    for j in range(1, l_e+1):
                        align[i][j][l_e][l_f] = count_align[i][j][l_e][l_f] / total_align[j][l_e][l_f]

        return t_ef, align

    def align(self, align_sent):
        """
        Returns the alignment result for one sentence pair. 
        """

        if self.probabilities is None or self.alignments is None:
            raise ValueError("The model does not train.")

        alignment = []

        l_e = len(align_sent.words)
        l_f = len(align_sent.mots)

        for j, en_word in enumerate(align_sent.words):
            
            # Initialize the maximum probability with Null token
            max_align_prob = (self.probabilities[en_word][None]*self.alignments[0][j+1][l_e][l_f], None)
            for i, fr_word in enumerate(align_sent.mots):
                # Find out the maximum probability
                max_align_prob = max(max_align_prob,
                    (self.probabilities[en_word][fr_word]*self.alignments[i+1][j+1][l_e][l_f], i))

            # If the maximum probability is not Null token,
            # then append it to the alignment. 
            if max_align_prob[1] is not None:
                alignment.append((j, max_align_prob[1]))

        return AlignedSent(align_sent.words, align_sent.mots, alignment)

# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
