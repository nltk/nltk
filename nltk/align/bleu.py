# -*- coding: utf-8 -*-
# Natural Language Toolkit: BLEU
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import division

import math

from nltk.util import ngrams
from nltk import word_tokenize


class BLEU(object):
    """
    This class implements the BLEU method, which is used to evaluate
    the quality of machine translation.

    The BLEU method mainly consists of two parts:

    Part 1 - modified n-gram precision

    The normal precision method may lead to some wrong translations with
    high-precision, e.g., the translation, in which a word of reference
    repeats several times, has very high precision. So in the modified
    n-gram precision, a reference word will be considered exhausted after
    a matching candidate word is identified.

    Part 2 - brevity penalty

    As the modified n-gram precision still has the problem from the short
    length sentence, brevity penalty is used to modify the overall BLEU
    score according to length.

    1. Test with an instance:

    >>> weights = [0.25, 0.25, 0.25, 0.25]
    >>> candidate1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...				  'ensures', 'that', 'the', 'military', 'always',
    ...				  'obeys', 'the', 'commands', 'of', 'the', 'party', '.']

    >>> candidate2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
    ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
    ...               'that', 'party', 'direct', '.']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...               'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...               'heed', 'Party', 'commands', '.']

    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...               'guarantees', 'the', 'military', 'forces', 'always',
    ...               'being', 'under', 'the', 'command', 'of', 'the',
    ...               'Party', '.']

    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...               'army', 'always', 'to', 'heed', 'the', 'directions',
    ...               'of', 'the', 'party', '.']

    >>> BLEU.compute(candidate1, [reference1, reference2, reference3], weights)
    0.0555...

    >>> BLEU.compute(candidate2, [reference1, reference2, reference3], weights)
    0.0421...

    2. Test with two corpus that one is a reference and another is
    an output from translation system:

    >>> weights = [0.25, 0.25, 0.25, 0.25]
    >>> ref_file = open('newstest2012-ref.en')  # doctest: +SKIP
    >>> candidate_file = open('newstest2012.fr-en.cmu-avenue')  # doctest: +SKIP

    >>> total = 0.0
    >>> count = 0

    >>> for candi_raw in candidate_file:  # doctest: +SKIP
    ...		ref_raw = ref_file.readline()
    ...		ref_tokens = word_tokenize(ref_raw)
    ...		candi_tokens = word_tokenize(candi_raw)
    ...		total = BLEU.compute(candi_tokens, [ref_tokens], weights)
    ...		count += 1

    >>> total / count  # doctest: +SKIP
    2.787504437460048e-05

    """

    @staticmethod
    def compute(candidate, references, weights):
        candidate = [c.lower() for c in candidate]
        references = [[r.lower() for r in reference] for reference in references]

        p_ns = (BLEU.modified_precision(candidate, references, i) for i, _ in enumerate(weights, start=1))
        s = math.fsum(w * math.log(p_n) for w, p_n in zip(weights, p_ns))

        bp = BLEU.brevity_penalty(candidate, references)
        return bp * math.exp(s)

    @staticmethod
    def modified_precision(candidate, references, n):

        candidate_ngrams = list(ngrams(candidate, n))
        c_words = set(candidate_ngrams)

        if not c_words:
            return 0

        for word in c_words:
            count_w = candidate_ngrams.count(word) + 1

            count_max = 0
            for reference in references:
                reference_ngrams = list(ngrams(reference, n))

                count = reference_ngrams.count(word) + 1
                count_max = max(count, count_max)

        # TODO: count_w == candidate_ngrams.count(c_words[-1]) + 1
        # (even though c_words is a set, so there is no last element, it's the last element returned by the iterator.)
        # Is it the desired behavior?
        return min(count_w, count_max) / (len(candidate) + len(c_words))

    @staticmethod
    def brevity_penalty(candidate, references):
        c = len(candidate)
        r = min(abs(len(r) - c) for r in references)

        if c > r:
            return 1
        else:
            return math.exp(1 - r / c)

# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod()
