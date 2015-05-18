# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 1
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Chin Yee Lee <c.lee32@student.unimelb.edu.au>
#         Hengfeng Li <hengfeng12345@gmail.com>
#         Ruxin Hou <r.hou@student.unimelb.edu.au>
#         Calvin Tanujaya Lim <c.tanujayalim@gmail.com>
# Based on earlier version by:
#         Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__  import division
from collections import defaultdict
from nltk.align  import AlignedSent

class IBMModel1(object):
    """
    This class implements the algorithm of Expectation Maximization for 
    the IBM Model 1. 

    Step 1 - Collect the evidence of a English word being translated by a 
             foreign language word.

    Step 2 - Estimate the probability of translation according to the 
             evidence from Step 1. 

    >>> from nltk.corpus import comtrans
    >>> bitexts = comtrans.aligned_sents()[:100]
    >>> ibm = IBMModel1(bitexts, 20)

    >>> aligned_sent = ibm.align(bitexts[6])
    >>> aligned_sent.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, 7), (4, 7), (5, 8)])
    >>> print('{0:.3f}'.format(bitexts[6].precision(aligned_sent)))
    0.556
    >>> print('{0:.3f}'.format(bitexts[6].recall(aligned_sent)))
    0.833
    >>> print('{0:.3f}'.format(bitexts[6].alignment_error_rate(aligned_sent)))
    0.333
    
    """
    def __init__(self, align_sents, num_iter):
        self.probabilities = self.train(align_sents, num_iter)

    def train(self, align_sents, num_iter):
        """
        Return the translation probability model trained by IBM model 1. 

        Arguments:
        align_sents   -- A list of instances of AlignedSent class, which
                        contains sentence pairs. 
        num_iter     -- The number of iterations.

        Returns:
        t_ef         -- A dictionary of translation probabilities. 
        """

        # Vocabulary of each language
        fr_vocab = set()
        en_vocab = set()
        for alignSent in align_sents:
            en_vocab.update(alignSent.words)
            fr_vocab.update(alignSent.mots)
        # Add the Null token
        fr_vocab.add(None)

        # Initial probability
        init_prob = 1 / len(en_vocab)

        # Create the translation model with initial probability
        t_ef = defaultdict(lambda: defaultdict(lambda: init_prob))

        total_e = defaultdict(lambda: 0.0)

        for i in range(0, num_iter):
            count_ef = defaultdict(lambda: defaultdict(lambda: 0.0))
            total_f = defaultdict(lambda: 0.0)

            for alignSent in align_sents:
                en_set = alignSent.words
                fr_set = [None] + alignSent.mots  

                # Compute normalization
                for e in en_set:
                    total_e[e] = 0.0
                    for f in fr_set:
                        total_e[e] += t_ef[e][f]

                # Collect counts
                for e in en_set:
                    for f in fr_set:
                        c = t_ef[e][f] / total_e[e]
                        count_ef[e][f] += c
                        total_f[f] += c

            # Compute the estimate probabilities
            for f in fr_vocab:
                for e in en_vocab:
                    t_ef[e][f] = count_ef[e][f] / total_f[f]

        return t_ef

    def align(self, align_sent):
        """
        Returns the alignment result for one sentence pair. 
        """

        if self.probabilities is None:
            raise ValueError("The model does not train.")

        alignment = []

        for j, en_word in enumerate(align_sent.words):
            
            # Initialize the maximum probability with Null token
            max_align_prob = (self.probabilities[en_word][None], None)
            for i, fr_word in enumerate(align_sent.mots):
                # Find out the maximum probability
                max_align_prob = max(max_align_prob,
                    (self.probabilities[en_word][fr_word], i))

            # If the maximum probability is not Null token,
            # then append it to the alignment. 
            if max_align_prob[1] is not None:
                alignment.append((j, max_align_prob[1]))

        return AlignedSent(align_sent.words, align_sent.mots, alignment)

# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
