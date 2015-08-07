# -*- coding: utf-8 -*-
# Natural Language Toolkit: IBM Model 3
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
phi: Fertility, the number of target words produced by a source word
p1: Probability that a target word produced by a source word is
    accompanied by another target word that is aligned to NULL
p0: 1 - p1

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
from nltk.align.ibm2 import IBMModel2
from math import factorial


class HashableDict(dict):
    """
    Hashable dictionary which can be put into a set.
    """

    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


class IBMModel3(object):
    """
    Translation model that considers how a word can be aligned to
    multiple words in another language

    >>> align_sents = []
    >>> align_sents.append(AlignedSent(['klein', 'ist', 'das', 'Haus'], ['the', 'house', 'is', 'small']))
    >>> align_sents.append(AlignedSent(['das', 'Haus'], ['the', 'house']))
    >>> align_sents.append(AlignedSent(['das', 'Buch'], ['the', 'book']))
    >>> align_sents.append(AlignedSent(['ein', 'Buch'], ['a', 'book']))

    >>> ibm3 = IBMModel3(align_sents, 5)

    >>> print('{0:.1f}'.format(ibm3.translation_table['Buch']['book']))
    1.0
    >>> print('{0:.1f}'.format(ibm3.translation_table['das']['book']))
    0.0
    >>> print('{0:.1f}'.format(ibm3.translation_table[None]['book']))
    0.0

    >>> aligned_sent = ibm3.align(align_sents[0])
    >>> aligned_sent.words
    ['klein', 'ist', 'das', 'Haus']
    >>> aligned_sent.mots
    ['the', 'house', 'is', 'small']
    >>> aligned_sent.alignment
    Alignment([(0, 2), (1, 3), (2, 0), (3, 1)])

    """

    def __init__(self, sentence_aligned_corpus, iterations):
        """
        Train on ``sentence_aligned_corpus`` and create a
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

        # Avoid division by zero errors by initializing probabilities to
        # a tiny value. Note that this approach is mathematically
        # incorrect, since it may create probabilities that sum to more
        # than 1
        self.PROB_SMOOTH = 0.1

        self.translation_table = defaultdict(lambda: defaultdict(lambda: float))
        """
        Probability(target word | source word). Values accessed as
        ``translation_table[target_word][source_word].``
        """

        self.distortion_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                lambda: self.PROB_SMOOTH))))
        """
        Probability(j | i,l,m). Values accessed as
        ``distortion_table[j][i][l][m].``
        """

        self.fertility_table = defaultdict(
            lambda: defaultdict(lambda: self.PROB_SMOOTH))
        """
        Probability(fertility | source word). Values accessed as
        ``fertility_table[fertility][source_word].``
        """

        # Initial probability of null insertion
        self.p1 = 0.5
        """
        Probability that a generated word requires another target word
        that is aligned to NULL
        """

        # Get the translation and alignment probabilities from IBM model 2
        ibm2 = IBMModel2(sentence_aligned_corpus, iterations)
        self.translation_table = ibm2.translation_table

        # Alignment table is only used for hill climbing and is not part
        # of the output of Model 3 training
        self.__alignment_table = ibm2.alignment_table

        self.train(sentence_aligned_corpus, iterations)

    def train(self, parallel_corpus, iterations):
        """
        Learns and sets probability tables
        """

        src_vocab = set()
        trg_vocab = set()
        for aligned_sentence in parallel_corpus:
            trg_vocab.update(aligned_sentence.words)
            src_vocab.update(aligned_sentence.mots)
        # Add the NULL token
        src_vocab.add(None)

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
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                l = len(src_sentence) - 1
                m = len(trg_sentence)

                # Sample the alignment space
                sampled_alignments = self.sample(trg_sentence, src_sentence)

                total_count = 0.0

                # E step (a): Compute normalization factors to weigh counts
                for (alignment, fert) in sampled_alignments:
                    count = self.probability(
                        alignment, trg_sentence, src_sentence, fert)
                    total_count += count

                # E step (b): Collect counts
                for (alignment, fert) in sampled_alignments:
                    count = self.probability(
                        alignment, trg_sentence, src_sentence, fert)
                    normalized_count = count / total_count
                    null_count = 0

                    for j in range(1, m + 1):
                        t = trg_sentence[j - 1]
                        i = alignment[j]
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
                            if i == alignment[j]:
                                fertility += 1

                        s = src_sentence[i]
                        fertility_count[fertility][s] += normalized_count
                        fertility_count_for_any_phi[s] += normalized_count

                        if fertility > max_fertility:
                            max_fertility = fertility

            translation_table = defaultdict(lambda: defaultdict(lambda: 0.0))
            distortion_table = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
                    lambda: 0.0)))
            )
            fertility_table = defaultdict(lambda: defaultdict(lambda: 0.0))

            # M step: Update probabilities with maximum likelihood estimates
            # Lexical translation
            for s in src_vocab:
                for t in trg_vocab:
                    translation_table[t][s] = (count_t_given_s[t][s] /
                                                    count_any_t_given_s[s])

            # Distortion
            for aligned_sentence in parallel_corpus:
                trg_sentence = aligned_sentence.words
                src_sentence = [None] + aligned_sentence.mots
                l = len(src_sentence) - 1
                m = len(trg_sentence)

                for i in range(0, l + 1):
                    for j in range(1, m + 1):
                        distortion_table[j][i][l][m] = (
                            distortion_count[j][i][l][m] /
                            distortion_count_for_any_j[i][l][m])

            # Fertility
            for fertility in range(0, max_fertility + 1):
                for s in src_vocab:
                    fertility_table[fertility][s] = (
                        fertility_count[fertility][s] /
                        fertility_count_for_any_phi[s])

            # NULL-aligned words generation
            p1 = count_p1 / (count_p1 + count_p0)

            self.translation_table = translation_table
            self.distortion_table = distortion_table
            self.fertility_table = fertility_table
            self.p1 = p1

    def sample(self, trg_sentence, src_sentence):
        """
        Sample the most probable alignments from the entire alignment
        space

        First, peg one alignment point and determine the best alignment
        according to IBM Model 2. With this initial alignment, use hill
        climbing to determine the best alignment according to Model 3.
        This alignment and its neighbors are added to the sample set.
        This process is repeated by pegging different alignment points.

        Hill climbing may be stuck in a local maxima, hence the pegging
        and trying out of different alignments.
        """
        sampled_alignments = set()

        m = len(trg_sentence)
        l = len(src_sentence) - 1

        # Compute Normalization
        for i in range(0, l + 1):
            for j in range(1, m + 1):
                alignment = HashableDict()
                fertility_of_i = HashableDict()

                # Initialize all fertility to zero
                for ii in range(0, l + 1):
                    fertility_of_i[ii] = 0

                # Pegging one alignment point
                alignment[j] = i
                fertility_of_i[i] = 1

                for jj in range(1, m + 1):
                    if jj != j:
                        # Find the best alignment according to model 2
                        max_alignment_prob = 0
                        best_i = 1

                        for ii in range(0, l + 1):
                            s = src_sentence[ii]
                            t = trg_sentence[jj - 1]
                            alignment_prob = (self.translation_table[t][s] *
                                         self.__alignment_table[ii][jj][l][m])
                            if alignment_prob > max_alignment_prob:
                                max_alignment_prob = alignment_prob
                                best_i = ii

                        alignment[jj] = best_i
                        fertility_of_i[best_i] += 1

                alignment = self.hillclimb(
                    alignment, j, trg_sentence, src_sentence, fertility_of_i)
                neighbors = self.neighboring(
                    alignment, j, trg_sentence, src_sentence, fertility_of_i)
                sampled_alignments.update(neighbors)

        return sampled_alignments

    def hillclimb(self, alignment, j_pegged,
                  trg_sentence, src_sentence, fertility_of_i):
        """
        Starting from ``alignment``, look at neighboring alignments
        iteratively for the best one

        There is no guarantee that the best alignment in the alignment
        space will be found, because the algorithm might be stuck in a
        local maximum.

        :return: The best alignment found from hill climbing
        :rtype: AlignedSent
        """

        fertility_so_far = fertility_of_i

        while True:
            old_alignment = alignment

            for (neighbor_alignment, neighbor_fertility) in self.neighboring(
                    alignment, j_pegged, trg_sentence, src_sentence,
                    fertility_so_far):
                neighbor_probability = self.probability(
                    neighbor_alignment, trg_sentence, src_sentence,
                    neighbor_fertility)
                current_probability = self.probability(
                    alignment, trg_sentence, src_sentence,
                    fertility_so_far)

                if neighbor_probability > current_probability:
                    alignment = neighbor_alignment
                    fertility_so_far = neighbor_fertility

            if alignment == old_alignment:
                # Until there are no better alignments
                break

        return alignment

    def probability(self, alignment,
                    trg_sentence, src_sentence, fertility_of_i):
        """
        Probability of ``trg_sentence`` and ``alignment`` given
        ``src_sentence``
        """

        m = len(trg_sentence)
        l = len(src_sentence) - 1
        p1 = self.p1
        p0 = 1 - p1

        probability = 1.0

        # Combine NULL insertion probability
        probability *= (pow(p1, fertility_of_i[0]) *
                        pow(p0, m - 2 * fertility_of_i[0]))
        if probability == 0:
            return probability

        # Compute combination (m - fertility_of_i[0]) choose fertility_of_i[0]
        for i in range(1, fertility_of_i[0] + 1):
            probability *= (m - fertility_of_i[0] - i + 1) / i
            if probability == 0:
                return probability

        # Combine fertility probabilities
        for i in range(1, l + 1):
            probability *= (factorial(fertility_of_i[i]) *
                self.fertility_table[fertility_of_i[i]][src_sentence[i]])
            if probability == 0:
                return probability

        # Combine lexical and distortion probabilities
        for j in range(1, m + 1):
            t = trg_sentence[j - 1]
            i = alignment[j]
            s = src_sentence[i]

            probability *= self.translation_table[t][s]
            probability *= self.distortion_table[j][i][l][m]
            if probability == 0:
                return probability

        return probability

    def neighboring(self, alignment, j_pegged,
                    trg_sentence, src_sentence, fertility_of_i):
        """
        :return: Neighbors of ``alignment`` obtained by moving or
            swapping one alignment point, with the corresponding fertility
        :rtype: set(tuple(HashableDict(int), int))
        """

        neighbors = set()

        m = len(trg_sentence)
        l = len(src_sentence) - 1

        for j in range(1, m + 1):
            if j != j_pegged:
                # Add alignments that differ by one alignment point
                for i in range(0, l + 1):
                    new_alignment = HashableDict(alignment)
                    new_alignment[j] = i

                    new_fertility = fertility_of_i
                    if new_fertility[alignment[j]] > 0:
                        new_fertility = HashableDict(fertility_of_i)
                        new_fertility[alignment[j]] -= 1
                        new_fertility[i] += 1

                    neighbors.update([(new_alignment, new_fertility)])

        for j in range(1, m + 1):
            if j != j_pegged:
                # Add alignments that have two alignment points swapped
                for other_j in range(1, m + 1):
                    if other_j != j_pegged and other_j != j:
                        new_alignment = HashableDict(alignment)
                        new_fertility = fertility_of_i
                        new_alignment[j] = alignment[other_j]
                        new_alignment[other_j] = alignment[j]

                        neighbors.update([(new_alignment, new_fertility)])

        return neighbors

    def align(self, sentence_pair):
        """
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The original sentence pair is not modified. Results are
        undefined if ``sentence_pair`` is not in the training set.

        Note that the algorithm used is not strictly Model 3, because
        fertilities and NULL insertion probabilities are ignored.

        :param sentence_pair: A sentence in the source language and its
            counterpart sentence in the target language
        :type sentence_pair: AlignedSent

        :return: ``AlignedSent`` filled in with the best word alignment
        :rtype: AlignedSent
        """

        if self.translation_table is None or self.distortion_table is None:
            raise ValueError("The model has not been trained.")

        alignment = []

        m = len(sentence_pair.words)
        l = len(sentence_pair.mots)

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            best_alignment = (self.translation_table[trg_word][None] *
                              self.distortion_table[j + 1][0][l][m], 0)
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = (self.translation_table[trg_word][src_word] *
                              self.distortion_table[j + 1][i + 1][l][m])
                best_alignment = max(best_alignment, (align_prob, i))

            # If trg_word is not aligned to the NULL token,
            # add it to the viterbi_alignment.
            if best_alignment[1] is not None:
                alignment.append((j, best_alignment[1]))

        return AlignedSent(sentence_pair.words, sentence_pair.mots, alignment)


