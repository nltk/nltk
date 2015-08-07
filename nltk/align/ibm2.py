# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 2
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
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
l: Number of words in the source sentence
m: Number of words in the target sentence
s: A word in the source language
t: A word in the target language


IBM Model 2 improves on Model 1 by accounting for word order.
An alignment probability is introduced, a(i | j,l,m), which predicts
a source word position, given its aligned target word's position.

The EM algorithm used in Model 2 is:
E step - In the training data, collect counts, weighted by prior
         probabilities.
         (a) count how many times a source language word is translated
             into a target language word
         (b) count how many times a particular position in the source
             sentence is aligned to a particular position in the target
             sentence

M step - Estimate new probabilities based on the counts from the E step


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
from nltk.align.ibm1 import IBMModel1

class IBMModel2(object):
    """
    Lexical translation model that considers word order

    >>> from nltk.corpus import comtrans
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
        Train on ``align_sents`` and create
        a translation model and an alignment model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        Runs a few iterations of Model 1 training to initialize
        model parameters.

        :param align_sents: Sentence-aligned parallel corpus
        :type align_sents: list(AlignedSent)

        :param num_iter: Number of iterations to run training algorithm
        :type num_iter: int
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
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The original sentence pair is not modified. Results are
        undefined if ``align_sent`` is not in the training set.

        :param align_sent: A sentence in the source language and its
            counterpart sentence in the target language
        :type align_sent: AlignedSent

        :return: ``AlignedSent`` filled in with the best word alignment
        :rtype: AlignedSent
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
