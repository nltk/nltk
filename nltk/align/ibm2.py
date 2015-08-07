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
l: Number of words in the source sentence, excluding NULL
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

from __future__ import division
from collections import defaultdict
from nltk.align import AlignedSent
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

    def __init__(self, sentence_aligned_corpus, iterations):
        """
        Train on ``sentence_aligned_corpus`` and create
        a translation model and an alignment model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        Runs a few iterations of Model 1 training to initialize
        model parameters.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int
        """

        output = self.train(sentence_aligned_corpus, iterations)
        self.translation_table = output[0]
        """
        dict(dict(float)): probability(target word | source word). Values
            accessed with ``translation_table[target_word][source_word].``
        """

        self.alignment_table = output[1]
        """
        dict(dict(dict(dict(float)))): probability(i | j,l,m). Values
            accessed with ``alignment_table[i][j][m][l].``
        """

    def train(self, parallel_corpus, iterations):
        """
        :return: A 2-tuple containing a dictionary of translation
            probabilities and a dictionary of alignment probabilities
        :rtype: tuple(dict(dict(int)), dict(dict(dict(dict(int)))))
        """

        # Get initial translation probability distribution
        # from a few iterations of Model 1 training.
        ibm1 = IBMModel1(parallel_corpus, 10)
        translation_table = ibm1.translation_table

        # Vocabulary of each language
        src_vocab = set()
        trg_vocab = set()
        for aligned_sentence in parallel_corpus:
            trg_vocab.update(aligned_sentence.words)
            src_vocab.update(aligned_sentence.mots)
        # Add the NULL token
        src_vocab.add(None)

        alignment_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                lambda: float))))

        # Initialize the distribution of alignment probability,
        # a(i | j,l,m) = 1 / (l+1) for all i, j, l, m
        for aligned_sentence in parallel_corpus:
            trg_sentence = aligned_sentence.words
            src_sentence = [None] + aligned_sentence.mots
            l = len(src_sentence) - 1  # exclude NULL token
            m = len(trg_sentence)
            initial_value = 1 / (l + 1)
            for i in range(0, l + 1):
                for j in range(1, m + 1):
                    alignment_table[i][j][m][l] = initial_value

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

            total_count = defaultdict(float)

            for aligned_sentence in parallel_corpus:
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                l = len(src_sentence) - 1
                m = len(trg_sentence)

                # E step (a): Compute normalization factors to weigh counts
                for j in range(1, m + 1):
                    t = trg_sentence[j - 1]
                    total_count[t] = 0
                    for i in range(0, l + 1):
                        s = src_sentence[i]
                        count = (translation_table[t][s] *
                                 alignment_table[i][j][m][l])
                        total_count[t] += count

                # E step (b): Collect counts
                for j in range(1, m + 1):
                    t = trg_sentence[j - 1]
                    for i in range(0, l + 1):
                        s = src_sentence[i]
                        count = (translation_table[t][s] *
                                 alignment_table[i][j][m][l])
                        normalized_count = count / total_count[t]

                        count_t_given_s[t][s] += normalized_count
                        count_any_t_given_s[s] += normalized_count
                        alignment_count[i][j][m][l] += normalized_count
                        alignment_count_for_any_i[j][m][l] += normalized_count

            translation_table = defaultdict(lambda: defaultdict(lambda: 0.0))
            alignment_table = defaultdict(lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))

            # Perform Laplace smoothing of alignment counts.
            # Note that smoothing is not in the original IBM Model 2 algorithm.
            for aligned_sentence in parallel_corpus:
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                l = len(src_sentence) - 1
                m = len(trg_sentence)

                laplace = 1.0
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        value = alignment_count[i][j][m][l]
                        if 0 < value < laplace:
                            laplace = value

                laplace *= 0.5
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        alignment_count[i][j][m][l] += laplace

                initial_value = laplace * m
                for j in range(1, m + 1):
                    alignment_count_for_any_i[j][m][l] += initial_value

            # M step: Update probabilities with maximum likelihood estimates
            for s in src_vocab:
                for t in trg_vocab:
                    translation_table[t][s] = (count_t_given_s[t][s] /
                                               count_any_t_given_s[s])

            for aligned_sentence in parallel_corpus:
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                l = len(src_sentence) - 1
                m = len(trg_sentence)
                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        alignment_table[i][j][m][l] = (
                            alignment_count[i][j][m][l] /
                            alignment_count_for_any_i[j][m][l])

        return translation_table, alignment_table

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

        m = len(sentence_pair.words)
        l = len(sentence_pair.mots)

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            best_alignment = (self.translation_table[trg_word][None] *
                              self.alignment_table[0][j + 1][m][l], None)
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = (self.translation_table[trg_word][src_word] *
                              self.alignment_table[i + 1][j + 1][m][l])
                best_alignment = max(best_alignment, (align_prob, i))

            # If trg_word is not aligned to the NULL token,
            # add it to the viterbi_alignment.
            if best_alignment[1] is not None:
                alignment.append((j, best_alignment[1]))

        return AlignedSent(sentence_pair.words, sentence_pair.mots, alignment)


# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
