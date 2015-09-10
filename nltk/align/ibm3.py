# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 3
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Translation model that considers how a word can be aligned to
multiple words in another language.

IBM Model 3 improves on Model 2 by directly modeling the phenomenon
where a word in one language may be translated into zero or more words
in another. This is expressed by the fertility probability,
n(phi | source word).

If a source word translates into more than one word, it is possible to
generate sentences that have the same alignment in multiple ways. This
is modeled by a distortion step. The distortion probability, d(j|i,l,m),
predicts a target word position, given its aligned source word's
position. The distortion probability replaces the alignment probability
of Model 2.

The fertility probability is not applicable for NULL. Target words that
align to NULL are assumed to be distributed uniformly in the target
sentence. The existence of these words is modeled by p1, the probability
that a target word produced by a real source word requires another
target word that is produced by NULL.

The EM algorithm used in Model 3 is:
E step - In the training data, collect counts, weighted by prior
         probabilities.
         (a) count how many times a source language word is translated
             into a target language word
         (b) count how many times a particular position in the target
             sentence is aligned to a particular position in the source
             sentence
         (c) count how many times a source word is aligned to phi number
             of target words
         (d) count how many times NULL is aligned to a target word

M step - Estimate new probabilities based on the counts from the E step

Because there are too many possible alignments, only the most probable
ones are considered. First, the best alignment is determined using prior
probabilities. Then, a hill climbing approach is used to find other good
candidates.


Notations:
i: Position in the source sentence
    Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
j: Position in the target sentence
    Valid values are 1, 2, ..., length of target sentence
l: Number of words in the source sentence, excluding NULL
m: Number of words in the target sentence
s: A word in the source language
t: A word in the target language
phi: Fertility, the number of target words produced by a source word
p1: Probability that a target word produced by a source word is
    accompanied by another target word that is aligned to NULL
p0: 1 - p1


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
from math import factorial
from nltk.align import AlignedSent
from nltk.align import Alignment
from nltk.align import IBMModel
from nltk.align import IBMModel2
import warnings


class IBMModel3(IBMModel):
    """
    Translation model that considers how a word can be aligned to
    multiple words in another language

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'ist', 'ja', 'groß'], ['the', 'house', 'is', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['ein', 'haus', 'ist', 'klein'], ['a', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))
    >>> bitext.append(AlignedSent(['ich', 'fasse', 'das', 'buch', 'zusammen'], ['i', 'summarize', 'the', 'book']))
    >>> bitext.append(AlignedSent(['fasse', 'zusammen'], ['summarize']))

    >>> ibm3 = IBMModel3(bitext, 5)

    >>> print('{0:.3f}'.format(ibm3.translation_table['buch']['book']))
    1.000
    >>> print('{0:.3f}'.format(ibm3.translation_table['das']['book']))
    0.000
    >>> print('{0:.3f}'.format(ibm3.translation_table['ja'][None]))
    1.000

    >>> print('{0:.3f}'.format(ibm3.distortion_table[1][1][2][2]))
    1.000
    >>> print('{0:.3f}'.format(ibm3.distortion_table[1][2][2][2]))
    0.000
    >>> print('{0:.3f}'.format(ibm3.distortion_table[2][2][4][5]))
    0.750

    >>> print('{0:.3f}'.format(ibm3.fertility_table[2]['summarize']))
    1.000
    >>> print('{0:.3f}'.format(ibm3.fertility_table[1]['book']))
    1.000

    >>> print('{0:.3f}'.format(ibm3.p1))
    0.026

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, None), (4, 3)])

    """

    def __init__(self, sentence_aligned_corpus, iterations):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model, a distortion model, a fertility model, and a
        model for generating NULL-aligned words.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        Runs a few iterations of Model 2 training to initialize
        model parameters.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int
        """
        super(IBMModel3, self).__init__(sentence_aligned_corpus)

        self.distortion_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                lambda: self.MIN_PROB))))
        """
        dict[int][int][int][int]: float. Probability(j | i,l,m).
        Values accessed as ``distortion_table[j][i][l][m]``.
        """

        # Get the translation and alignment probabilities from IBM model 2
        ibm2 = IBMModel2(sentence_aligned_corpus, iterations)
        self.translation_table = ibm2.translation_table

        # Alignment table is only used for hill climbing and is not part
        # of the output of Model 3 training
        self.alignment_table = ibm2.alignment_table

        # Initialize the distribution of distortion probability,
        # d(j | i,l,m) = 1 / m for all i, j, l, m
        for aligned_sentence in sentence_aligned_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)
            initial_value = 1 / m
            if initial_value > IBMModel.MIN_PROB:
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        self.distortion_table[j][i][l][m] = initial_value
            else:
                warnings.warn("Target sentence is too long (" + str(m) +
                              " words). Results may be less accurate.")

        self.train(sentence_aligned_corpus, iterations)

    def train(self, parallel_corpus, iterations):
        for k in range(0, iterations):
            max_fertility = 0

            # Reset all counts
            count_t_given_s = defaultdict(lambda: defaultdict(lambda: 0.0))
            count_any_t_given_s = defaultdict(lambda: 0.0)

            distortion_count = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                    lambda: 0.0))))
            distortion_count_for_any_j = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: 0.0)))

            count_p0 = 0.0
            count_p1 = 0.0

            fertility_count = defaultdict(lambda: defaultdict(lambda: 0.0))
            fertility_count_for_any_phi = defaultdict(lambda: 0.0)

            for aligned_sentence in parallel_corpus:
                src_sentence = [None] + aligned_sentence.mots
                trg_sentence = ['UNUSED'] + aligned_sentence.words  # 1-indexed
                l = len(aligned_sentence.mots)
                m = len(aligned_sentence.words)

                # Sample the alignment space
                sampled_alignments, best_alignment = self.sample(
                    aligned_sentence)
                # Record the most probable alignment
                aligned_sentence.alignment = Alignment(
                    best_alignment.zero_indexed_alignment())

                total_count = 0.0

                # E step (a): Compute normalization factors to weigh counts
                for alignment_info in sampled_alignments:
                    count = self.prob_t_a_given_s(alignment_info)
                    total_count += count

                # E step (b): Collect counts
                for alignment_info in sampled_alignments:
                    count = self.prob_t_a_given_s(alignment_info)
                    normalized_count = count / total_count
                    null_count = 0

                    for j in range(1, m + 1):
                        t = trg_sentence[j]
                        i = alignment_info.alignment[j]
                        s = src_sentence[i]

                        # Lexical translation
                        count_t_given_s[t][s] += normalized_count
                        count_any_t_given_s[s] += normalized_count

                        # Distortion
                        distortion_count[j][i][l][m] += normalized_count
                        distortion_count_for_any_j[i][l][m] += normalized_count

                        if i == 0:
                            null_count += 1

                    # NULL-aligned words generation
                    count_p1 += null_count * normalized_count
                    count_p0 += (m - 2 * null_count) * normalized_count

                    # Fertility
                    for i in range(0, l + 1):
                        fertility = 0

                        for j in range(1, m + 1):
                            if i == alignment_info.alignment[j]:
                                fertility += 1

                        s = src_sentence[i]
                        fertility_count[fertility][s] += normalized_count
                        fertility_count_for_any_phi[s] += normalized_count

                        if fertility > max_fertility:
                            max_fertility = fertility

            # M step: Update probabilities with maximum likelihood estimates
            # If any probability is less than MIN_PROB, clamp it to MIN_PROB
            MIN_PROB = IBMModel.MIN_PROB

            # Lexical translation
            for s in self.src_vocab:
                for t in self.trg_vocab:
                    estimate = count_t_given_s[t][s] / count_any_t_given_s[s]
                    self.translation_table[t][s] = max(estimate, MIN_PROB)

            # Distortion
            for aligned_sentence in parallel_corpus:
                l = len(aligned_sentence.mots)
                m = len(aligned_sentence.words)

                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        estimate = (distortion_count[j][i][l][m] /
                                    distortion_count_for_any_j[i][l][m])
                        self.distortion_table[j][i][l][m] = max(estimate,
                                                                MIN_PROB)

            # Fertility
            for fertility in range(0, max_fertility + 1):
                for s in self.src_vocab:
                    estimate = (fertility_count[fertility][s] /
                                fertility_count_for_any_phi[s])
                    self.fertility_table[fertility][s] = max(estimate, MIN_PROB)

            # NULL-aligned words generation
            p1_estimate = count_p1 / (count_p1 + count_p0)
            p1_estimate = max(p1_estimate, MIN_PROB)

            # Clip p1 if it is too large, because p0 = 1 - p1 should
            # not be smaller than MIN_PROB
            self.p1 = min(p1_estimate, 1 - MIN_PROB)

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        src_sentence = alignment_info.src_sentence
        trg_sentence = alignment_info.trg_sentence
        l = len(src_sentence) - 1  # exclude NULL
        m = len(trg_sentence) - 1
        p1 = self.p1
        p0 = 1 - p1

        probability = 1.0
        MIN_PROB = IBMModel.MIN_PROB

        # Combine NULL insertion probability
        null_fertility = alignment_info.fertility_of_i(0)
        probability *= (pow(p1, null_fertility) *
                        pow(p0, m - 2 * null_fertility))
        if probability < MIN_PROB:
            return MIN_PROB

        # Compute combination (m - null_fertility) choose null_fertility
        for i in range(1, null_fertility + 1):
            probability *= (m - null_fertility - i + 1) / i
            if probability < MIN_PROB:
                return MIN_PROB

        # Combine fertility probabilities
        for i in range(1, l + 1):
            fertility = alignment_info.fertility_of_i(i)
            probability *= (factorial(fertility) *
                self.fertility_table[fertility][src_sentence[i]])
            if probability < MIN_PROB:
                return MIN_PROB

        # Combine lexical and distortion probabilities
        for j in range(1, m + 1):
            t = trg_sentence[j]
            i = alignment_info.alignment[j]
            s = src_sentence[i]

            probability *= (self.translation_table[t][s] *
                self.distortion_table[j][i][l][m])
            if probability < MIN_PROB:
                return MIN_PROB

        return probability
