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
Lexical translation model that ignores word order.

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


Notations:
i: Position in the source sentence
    Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
j: Position in the target sentence
    Valid values are 1, 2, ..., length of target sentence
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

from __future__  import division
from collections import defaultdict
from nltk.align  import AlignedSent
from nltk.align.ibm_model import IBMModel
import warnings


class IBMModel1(IBMModel):
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

    def __init__(self, sentence_aligned_corpus, iterations):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int
        """

        super(IBMModel1, self).__init__(sentence_aligned_corpus)

        # seed with a uniform distribution
        initial_prob = 1 / len(self.trg_vocab)
        if initial_prob > IBMModel.MIN_PROB:
            for t in self.trg_vocab:
                for s in self.src_vocab:
                    self.translation_table[t][s] = initial_prob
        else:
            warnings.warn("Target language vocabulary is too large. "
                          "Results may be less accurate.")

        self.train(sentence_aligned_corpus, iterations)

    def train(self, parallel_corpus, iterations):
        for i in range(0, iterations):
            count_t_given_s = defaultdict(lambda: defaultdict(lambda: 0.0))
            count_any_t_given_s = defaultdict(lambda: 0.0)

            for aligned_sentence in parallel_corpus:
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                total_count = defaultdict(lambda: 0.0)

                # E step (a): Compute normalization factors to weigh counts
                for t in trg_sentence:
                    if total_count[t] == 0.0:
                        for s in src_sentence:
                            total_count[t] += self.translation_table[t][s]

                # E step (b): Collect counts
                for t in trg_sentence:
                    for s in src_sentence:
                        count = self.translation_table[t][s]
                        normalized_count = count / total_count[t]
                        count_t_given_s[t][s] += normalized_count
                        count_any_t_given_s[s] += normalized_count

            # M step: Update probabilities with maximum likelihood estimate
            for s in self.src_vocab:
                for t in self.trg_vocab:
                    estimate = count_t_given_s[t][s] / count_any_t_given_s[s]
                    self.translation_table[t][s] = max(estimate,
                                                       IBMModel.MIN_PROB)

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

        if self.translation_table is None:
            raise ValueError("The model has not been trained.")

        alignment = []

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            initial_prob = max(self.translation_table[trg_word][None],
                               IBMModel.MIN_PROB)
            best_alignment = (initial_prob, None)
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = self.translation_table[trg_word][src_word]
                best_alignment = max(best_alignment, (align_prob, i))

            # If trg_word is not aligned to the NULL token,
            # add it to the viterbi_alignment.
            if best_alignment[1] is not None:
                alignment.append((j, best_alignment[1]))

        return AlignedSent(sentence_pair.words, sentence_pair.mots, alignment)

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
