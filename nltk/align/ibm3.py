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
l: Number of words in the source sentence
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

from __future__  import division
from collections import defaultdict
from nltk.align  import AlignedSent
from nltk.align.ibm2 import IBMModel2
from math import factorial

class HashableDict(dict):
    """
    Hashable dictionary which can be put into a set.
    """
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))

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

    >>> print('{0:.1f}'.format(ibm3.probabilities['Buch']['book']))
    1.0
    >>> print('{0:.1f}'.format(ibm3.probabilities['das']['book']))
    0.0
    >>> print('{0:.1f}'.format(ibm3.probabilities[None]['book']))
    0.0

    >>> aligned_sent = ibm3.align(align_sents[0])
    >>> aligned_sent.words
    ['klein', 'ist', 'das', 'Haus']
    >>> aligned_sent.mots
    ['the', 'house', 'is', 'small']
    >>> aligned_sent.alignment
    Alignment([(0, 2), (1, 3), (2, 0), (3, 1)])

    """

    def __init__(self, align_sents, num_iter):
        """
        Train on ``align_sents`` and create a
        translation model, a distortion model, a fertility model, and a
        model for generating NULL-aligned words.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        Runs a few iterations of Model 2 training to initialize
        model parameters.

        :param align_sents: Sentence-aligned parallel corpus
        :type align_sents: list(AlignedSent)

        :param num_iter: Number of iterations to run training algorithm
        :type num_iter: int
        """

        # If there is not an initial value, it throws an exception of 
        # the number divided by zero. And the value of computing 
        # probability will be always zero.
        self.PROB_SMOOTH = 0.1

        self.train(align_sents, num_iter)


    def train(self, align_sents, num_iter):
        """
        Learns and sets probability tables
        """
        # Get the translation and alignment probabilities from IBM model 2
        ibm2 = IBMModel2(align_sents, num_iter)
        self.probabilities, self.align_table = ibm2.probabilities, ibm2.alignments

        fr_vocab = set()
        en_vocab = set()
        for alignSent in align_sents:
            en_vocab.update(alignSent.words)
            fr_vocab.update(alignSent.mots)
        fr_vocab.add(None)

        # Initial probability of null insertion.
        self.null_insertion = 0.5

        self.fertility = defaultdict(lambda: defaultdict(lambda: self.PROB_SMOOTH)) 
        self.distortion = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.PROB_SMOOTH))))

        for k in range(0, num_iter):
            max_fert = 0
            # Set all count* and total* to 0
            count_t = defaultdict(lambda: defaultdict(lambda: 0.0))
            total_t = defaultdict(lambda: 0.0)

            count_d = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
            total_d = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0)))

            count_p0 = 0.0
            count_p1 = 0.0

            count_f = defaultdict(lambda: defaultdict(lambda: 0.0))
            total_f = defaultdict(lambda: 0.0)

            for alignSent in align_sents:

                en_set = alignSent.words
                fr_set = [None] + alignSent.mots
                l_f = len(fr_set) - 1
                l_e = len(en_set)

                # Sample the alignment space
                A = self.sample( en_set, fr_set)
                
                # Collect counts
                c_total = 0.0

                for (a, fert) in A:
                    c_total += self.probability(a, en_set, fr_set, fert)

                for (a, fert) in A:
                    c = self.probability(a, en_set, fr_set, fert)/c_total
                    null = 0

                    for j in range(1, l_e+1):
                        en_word = en_set[j-1]
                        fr_word = fr_set[a[j]]

                        # Lexical translation
                        count_t[en_word][fr_word] += c
                        total_t[fr_word] += c

                        # Distortion
                        count_d[j][a[j]][l_e][l_f] += c
                        total_d[a[j]][l_e][l_f] += c

                        if a[j] == 0:
                            null += 1

                    # Collect the counts of null insetion
                    count_p1 += null * c
                    count_p0 += (l_e - 2 * null) * c

                    # Collect the counts of fertility
                    for i in range(0, l_f+1):
                        fertility = 0

                        for j in range(1, l_e+1):
                            if i == a[j]:
                                fertility += 1

                        fr_word = fr_set[i]
                        count_f[fertility][fr_word] += c
                        total_f[fr_word] += c

                        if fertility > max_fert:
                            max_fert = fertility

			
            self.probabilities = defaultdict(lambda: defaultdict(lambda: 0.0))
            self.distortion = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))	
            self.fertility = defaultdict(lambda: defaultdict(lambda: 0.0))

            # Estimate translation probability distribution
            for f in fr_vocab:
                for e in en_vocab:
                    self.probabilities[e][f] = count_t[e][f] / total_t[f]

            # Estimate distortion
            for alignSent in align_sents:
                en_set = alignSent.words
                fr_set = [None] + alignSent.mots
                l_f = len(fr_set) - 1
                l_e = len(en_set)

                for i in range(0, l_f+1):
                    for j in range(1, l_e+1):
                        self.distortion[j][i][l_e][l_f] = count_d[j][i][l_e][l_f] / total_d[i][l_e][l_f]

            # Estimate the fertility, n(Fertility | input word)
            for ferti in range(0, max_fert+1):
                for fr_word in fr_vocab:
                    self.fertility[ferti][fr_word] = count_f[ferti][fr_word] / total_f[fr_word]

            # Estimate the probability of null insertion
            p1 = count_p1 / (count_p1+count_p0)
            self.null_insertion = 1 - p1

    def sample(self, e, f):
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
        A = set()

        le = len(e)
        lf = len(f) - 1

        # Compute Normalization
        for i in range(0, lf+1):
            for j in range(1, le+1):
                a = HashableDict()
                fert = HashableDict()
                # Initialize all fertility to zero
                for ii in range(0, lf+1):
                    fert[ii] = 0

                # Pegging one alignment point
                a[j] = i
                fert[i] = 1

                for jj in range(1, le+1):
                    if jj != j:
                        # Find the best alignment according to model 2
                        maxalignment = 0
                        besti = 1

                        for ii in range(0, lf+1):
                            alignment = self.probabilities[e[jj-1]][f[ii]] * self.align_table[ii][jj][le][lf]
                            if alignment > maxalignment:
                                maxalignment = alignment
                                besti = ii

                        a[jj] = besti
                        fert[besti] += 1

                a = self.hillclimb(a, j, e, f, fert)
                neighbor = self.neighboring(a, j, e, f, fert)
                A.update(neighbor)

        return A

    def hillclimb(self, a, j_pegged, es, fs, fert):
        """
        Starting from ``a``, look at neighboring alignments
        iteratively for the best one

        There is no guarantee that the best alignment in the alignment
        space will be found, because the algorithm might be stuck in a
        local maximum.

        :return: The best alignment found from hill climbing
        :rtype: AlignedSent
        """
        so_far_fert = fert

        while True:
            a_old = a

            for (a_nerghbor, neighbor_Fert) in self.neighboring(a, j_pegged, es, fs, so_far_fert):
                if self.probability(a_nerghbor, es, fs, neighbor_Fert) > self.probability(a, es, fs, so_far_fert):
                    # If the probability of an alignment is higher than 
                    # the current alignment recorded, then replace the 
                    # current one. 
                    a = a_nerghbor
                    so_far_fert = neighbor_Fert

            if a == a_old:
                # Until this alignment is the highest one in local
                break

        return a

    def probability(self, a, es, fs, Fert):
        """
        Probability of ``es`` and ``a`` given
        ``fs``
        """
        l_e = len(es)
        l_f = len(fs) - 1
        p1 = 1 - self.null_insertion

        total = 1.0

        # Compute the NULL insertation
        total *= pow(p1, Fert[0]) * pow(self.null_insertion, l_e - 2 * Fert[0])
        if total == 0:
            return total

        # Compute the combination (l_e - Fert[0]) choose Fert[0]
        for i in range(1, Fert[0]+1):
            total *= (l_e - Fert[0] - i + 1) / i
            if total == 0:
                return total

        # Compute fertilities term
        for i in range(1, l_f+1):
            total *= factorial(Fert[i]) * self.fertility[Fert[i]][fs[i]]
            if total == 0:
                return total

        # Multiply the lexical and distortion probabilities
        for j in range(1, l_e+1):
            en_word = es[j-1]
            fr_word = fs[a[j]]

            total *= self.probabilities[en_word][fr_word]
            total *= self.distortion[j][a[j]][l_e][l_f]
            if total == 0:
                return total

        return total

    def neighboring(self, a, j_pegged, es, fs, fert):
        """
        :return: Neighbors of ``a`` obtained by moving or
            swapping one alignment point, with the corresponding fertility
        :rtype: set(tuple(HashableDict(int), int))
        """
        N = set()

        l_e = len(es)
        l_f = len(fs) - 1

        for j in range(1, l_e+1):
            if j != j_pegged:
                # Moves
                for i in range(0, l_f+1):
                    new_align = HashableDict(a)
                    new_align[j] = i

                    new_fert = fert
                    if new_fert[a[j]] > 0:
                        new_fert = HashableDict(fert)
                        new_fert[a[j]] -= 1
                        new_fert[i] += 1

                    N.update([(new_align, new_fert)])


        for j_one in range(1, l_e+1):
            if j_one != j_pegged:
                # Swaps
                for j_two in range(1, l_e+1):
                    if j_two != j_pegged and j_two != j_one:
                        new_align = HashableDict(a)
                        new_fert = fert
                        new_align[j_one] = a[j_two]
                        new_align[j_two] = a[j_one]

                        N.update([(new_align, new_fert)])

        return N

    def align(self, align_sent):
        """
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The original sentence pair is not modified. Results are
        undefined if ``align_sent`` is not in the training set.

        Note that the algorithm used is not strictly Model 3, because
        fertilities and NULL insertion probabilities are ignored.

        :param align_sent: A sentence in the source language and its
            counterpart sentence in the target language
        :type align_sent: AlignedSent

        :return: ``AlignedSent`` filled in with the best word alignment
        :rtype: AlignedSent
        """

        if self.probabilities is None or self.distortion is None:
            raise ValueError("The model does not train.")

        alignment = []

        l_e = len(align_sent.words)
        l_f = len(align_sent.mots)

        for j, en_word in enumerate(align_sent.words):
            
            # Initialize the maximum probability with Null token
            max_align_prob = (self.probabilities[en_word][None]*self.distortion[j+1][0][l_e][l_f], 0)
            for i, fr_word in enumerate(align_sent.mots):
                # Find out the maximum probability
                max_align_prob = max(max_align_prob,
                    (self.probabilities[en_word][fr_word]*self.distortion[j+1][i+1][l_e][l_f], i))

            # If the maximum probability is not Null token,
            # then append it to the alignment. 
            if max_align_prob[1] is not None:
                alignment.append((j, max_align_prob[1]))

        return AlignedSent(align_sent.words, align_sent.mots, alignment)

# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
