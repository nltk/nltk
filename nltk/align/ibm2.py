# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 2
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Lexical translation model that considers word order.

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


Notations:
i: Position in the source sentence
    Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
j: Position in the target sentence
    Valid values are 1, 2, ..., length of target sentence
l: Number of words in the source sentence, excluding NULL
m: Number of words in the target sentence
s: A word in the source language
t: A word in the target language


References:
Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

from __future__ import division
from collections import defaultdict
from nltk.align import AlignedSent
from nltk.align.ibm_model import IBMModel
from nltk.align.ibm1 import IBMModel1
import warnings


class IBMModel2(IBMModel):
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

    >>> from nltk.align.ibm_model import AlignmentInfo
    >>> alignment_info = AlignmentInfo((0, 1, 3, 4), [None] + aligned_sent.mots, ['UNUSED'] + aligned_sent.words, None)
    >>> prob_target_alignment = ibm.prob_t_a_given_s(alignment_info)
    >>> print('{0:.3f}'.format(prob_target_alignment))
    0.545

    """

    def __init__(self, sentence_aligned_corpus, iterations):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model and an alignment model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        Runs a few iterations of Model 1 training to initialize
        model parameters.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int
        """

        super(IBMModel2, self).__init__(sentence_aligned_corpus)

        # Get initial translation probability distribution
        # from a few iterations of Model 1 training.
        ibm1 = IBMModel1(sentence_aligned_corpus, 10)
        self.translation_table = ibm1.translation_table

        # Initialize the distribution of alignment probability,
        # a(i | j,l,m) = 1 / (l+1) for all i, j, l, m
        for aligned_sentence in sentence_aligned_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)
            initial_value = 1 / (l + 1)
            if initial_value > IBMModel.MIN_PROB:
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        self.alignment_table[i][j][l][m] = initial_value
            else:
                warnings.warn("Source sentence is too long (" + str(l) +
                              " words). Results may be less accurate.")

        self.train(sentence_aligned_corpus, iterations)

    def train(self, parallel_corpus, iterations):
        for i in range(0, iterations):
            count_t_given_s = defaultdict(lambda: defaultdict(float))
            count_any_t_given_s = defaultdict(float)

            # count of i given j, l, m
            alignment_count = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                    lambda: 0.0))))
            alignment_count_for_any_i = defaultdict(
                lambda: defaultdict(lambda: defaultdict(
                    lambda: 0.0)))

            for aligned_sentence in parallel_corpus:
                src_sentence = [None] + aligned_sentence.mots
                trg_sentence = ['UNUSED'] + aligned_sentence.words # 1-indexed
                l = len(aligned_sentence.mots)
                m = len(aligned_sentence.words)
                total_count = defaultdict(float)

                # E step (a): Compute normalization factors to weigh counts
                for j in range(1, m + 1):
                    t = trg_sentence[j]
                    total_count[t] = 0
                    for i in range(0, l + 1):
                        s = src_sentence[i]
                        count = (self.translation_table[t][s] *
                                 self.alignment_table[i][j][l][m])
                        total_count[t] += count

                # E step (b): Collect counts
                for j in range(1, m + 1):
                    t = trg_sentence[j]
                    for i in range(0, l + 1):
                        s = src_sentence[i]
                        count = (self.translation_table[t][s] *
                                 self.alignment_table[i][j][l][m])
                        normalized_count = count / total_count[t]

                        count_t_given_s[t][s] += normalized_count
                        count_any_t_given_s[s] += normalized_count
                        alignment_count[i][j][l][m] += normalized_count
                        alignment_count_for_any_i[j][l][m] += normalized_count

            # M step: Update probabilities with maximum likelihood estimates
            for s in self.src_vocab:
                for t in self.trg_vocab:
                    estimate = count_t_given_s[t][s] / count_any_t_given_s[s]
                    self.translation_table[t][s] = max(estimate,
                                                       IBMModel.MIN_PROB)

            for aligned_sentence in parallel_corpus:
                l = len(aligned_sentence.mots)
                m = len(aligned_sentence.words)
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        estimate = (alignment_count[i][j][l][m] /
                                    alignment_count_for_any_i[j][l][m])
                        self.alignment_table[i][j][l][m] = max(estimate,
                                                              IBMModel.MIN_PROB)

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """

        prob = 1.0
        l = len(alignment_info.src_sentence) - 1
        m = len(alignment_info.trg_sentence) - 1

        for j, i in enumerate(alignment_info.alignment):
            if j == 0:
                continue # skip the dummy zeroeth element
            trg_word = alignment_info.trg_sentence[j]
            src_word = alignment_info.src_sentence[i]
            prob *= (self.translation_table[trg_word][src_word] *
                     self.alignment_table[i][j][l][m])

        return max(prob, IBMModel.MIN_PROB)

    def align(self, sentence_pair):
        """
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The original sentence pair is not modified. Results are
        undefined if ``sentence_pair`` is not in the training set.

        :param sentence_pair: A sentence in the source language and its
            counterpart sentence in the target language
        :type sentence_pair: AlignedSent

        :return: ``AlignedSent`` filled in with the best word alignment
        :rtype: AlignedSent
        """

        if self.translation_table is None or self.alignment_table is None:
            raise ValueError("The model has not been trained.")

        alignment = []

        l = len(sentence_pair.mots)
        m = len(sentence_pair.words)

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            best_prob = (self.translation_table[trg_word][None] *
                         self.alignment_table[0][j + 1][l][m])
            best_prob = max(best_prob, IBMModel.MIN_PROB)
            best_alignment = None
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = (self.translation_table[trg_word][src_word] *
                              self.alignment_table[i + 1][j + 1][l][m])
                if align_prob >= best_prob:
                    best_prob = align_prob
                    best_alignment = i

            # If trg_word is not aligned to the NULL token,
            # add it to the viterbi_alignment.
            if best_alignment is not None:
                alignment.append((j, best_alignment))

        return AlignedSent(sentence_pair.words, sentence_pair.mots, alignment)
