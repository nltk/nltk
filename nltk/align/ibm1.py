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

"""
The IBM models are a series of generative models that learn lexical
translation probabilities, p(target language word|source language word),
given a sentence-aligned parallel corpus.

The models increase in sophistication from model 1 to 5. Typically, the
output of lower models is used to seed the higher models. All models
use the Expectation-Maximization (EM) algorithm to learn various
probability tables.

Words in a sentence are one-indexed. The first word of a sentence has
position 1, not 0. Index 0 is reserved in the source sentence for the
NULL token. The concept of position does not apply to NULL, but it is
indexed at 0 by convention.

Each target word is aligned to exactly one source word or the NULL
token.

Notations
i: Position in the source sentence
    Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
j: Position in the target sentence
    Valid values are 1, 2, ..., length of target sentence
s: A word in the source language
t: A word in the target language


In IBM Model 1, word order is ignored for simplicity. Thus, the
following two alignments are equally likely.

Source: je mange du jambon
Target: i eat some ham
Alignment: (1,1) (2,2) (3,3) (4,4)

Source: je mange du jambon
Target: some ham eat i
Alignment: (1,4) (2,3) (3,2) (4,1)

The EM algorithm used in Model 1 is:
E step - In the training data, count how many times a source language
         word is translated into a target language word, weighted by
         the prior probability of the translation.

M step - Estimate the new probability of translation based on the
         counts from the Expectation step.


References:
Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

from __future__  import division
from collections import defaultdict
from nltk.align  import AlignedSent

class IBMModel1(object):
    """
    Lexical translation model that ignores word order

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
        Train on ``align_sents`` and create
        a translation model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param align_sents: Sentence-aligned parallel corpus
        :type align_sents: list(AlignedSent)

        :param num_iter: Number of iterations to run training algorithm
        :type num_iter: int
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
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The original sentence pair is not modified. Results are
        undefined if ``sentence_pair`` is not in the training set.

        :param align_sent: A sentence in the source language and its
            counterpart sentence in the target language
        :type align_sent: AlignedSent

        :return: ``AlignedSent`` filled in with the best word alignment
        :rtype: AlignedSent
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
