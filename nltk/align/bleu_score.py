# -*- coding: utf-8 -*-
# Natural Language Toolkit: BLEU Score
#
# Copyright (C) 2001-2015 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# Contributors: Dmitrijs Milajevs
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""BLEU score implementation."""

from __future__ import division

import math

from nltk.tokenize import word_tokenize
from nltk.compat import Counter
from nltk.util import ngrams


def bleu(candidate, references, weights):
    """Calculate BLEU score (Bilingual Evaluation Understudy)

    :param candidate: a candidate sentence
    :type candidate: list(str)
    :param references: reference sentences
    :type references: list(list(str))
    :param weights: weights for unigrams, bigrams, trigrams and so on
    :type weights: list(float)

    >>> weights = [0.25, 0.25, 0.25, 0.25]
    >>> candidate1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...               'ensures', 'that', 'the', 'military', 'always',
    ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> candidate2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
    ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
    ...               'that', 'party', 'direct']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...               'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...               'heed', 'Party', 'commands']

    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...               'guarantees', 'the', 'military', 'forces', 'always',
    ...               'being', 'under', 'the', 'command', 'of', 'the',
    ...               'Party']

    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...               'army', 'always', 'to', 'heed', 'the', 'directions',
    ...               'of', 'the', 'party']

    >>> bleu(candidate1, [reference1, reference2, reference3], weights)
    0.504...

    >>> bleu(candidate2, [reference1, reference2, reference3], weights)
    0

    Papineni, Kishore, et al. "BLEU: A method for automatic evaluation of
    machine translation." Proceedings of the 40th annual meeting on association for
    computational linguistics. Association for Computational Linguistics, 2002.
    http://www.aclweb.org/anthology/P02-1040.pdf

    """
    p_ns = (
        _modified_precision(candidate, references, i)
        for i, _ in enumerate(weights, start=1)
    )

    try:
        s = math.fsum(w * math.log(p_n) for w, p_n in zip(weights, p_ns))
    except ValueError:
        # some p_ns is 0
        return 0

    bp = _brevity_penalty(candidate, references)
    return bp * math.exp(s)


def _modified_precision(candidate, references, n):
    """Calculate modified ngram precision.

    The normal precision method may lead to some wrong translations with
    high-precision, e.g., the translation, in which a word of reference
    repeats several times, has very high precision. So in the modified
    n-gram precision, a reference word will be considered exhausted after
    a matching candidate word is identified.

    Paper examples:

    >>> _modified_precision(
    ...    'the the the the the the the'.split(),
    ...    ['the cat is on the mat'.split(), 'there is a cat on the mat'.split()],
    ...    n=1,
    ... )
    0.28...

    >>> _modified_precision(
    ...    'the the the the the the the'.split(),
    ...    ['the cat is on the mat'.split(), 'there is a cat on the mat'.split()],
    ...    n=2,
    ... )
    0.0

    >>> _modified_precision(
    ...    'of the'.split(),
    ...    [
    ...        'It is a guide to action that ensures that the military will forever heed Party commands.'.split(),
    ...        'It is the guiding principle which guarantees the military forces always being under the command of the Party.'.split(),
    ...        'It is the practical guide for the army always to heed the directions of the party'.split(),
    ...    ],
    ...    n=1,
    ... )
    1.0

    >>> _modified_precision(
    ...    'of the'.split(),
    ...    [
    ...        'It is a guide to action that ensures that the military will forever heed Party commands.'.split(),
    ...        'It is the guiding principle which guarantees the military forces always being under the command of the Party.'.split(),
    ...        'It is the practical guide for the army always to heed the directions of the party'.split(),
    ...    ],
    ...    n=2,
    ... )
    1.0

    More examples:

    >>> weights = [0.25, 0.25, 0.25, 0.25]
    >>> candidate1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...               'ensures', 'that', 'the', 'military', 'always',
    ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> candidate2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
    ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
    ...               'that', 'party', 'direct']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...               'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...               'heed', 'Party', 'commands']

    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...               'guarantees', 'the', 'military', 'forces', 'always',
    ...               'being', 'under', 'the', 'command', 'of', 'the',
    ...               'Party']

    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...               'army', 'always', 'to', 'heed', 'the', 'directions',
    ...               'of', 'the', 'party']

    Unigrams:

    >>> _modified_precision(
    ...    candidate1,
    ...    [reference1, reference2, reference3],
    ...    n=1,
    ... )
    0.94...

    >>> _modified_precision(
    ...    candidate2,
    ...    [reference1, reference2, reference3],
    ...    n=1,
    ... )
    0.57...

    Bigrams:

    >>> _modified_precision(
    ...    candidate1,
    ...    [reference1, reference2, reference3],
    ...    n=2,
    ... )
    0.58...

    >>> _modified_precision(
    ...    candidate2,
    ...    [reference1, reference2, reference3],
    ...    n=2,
    ... )
    0.07...

    """
    counts = Counter(ngrams(candidate, n))

    if not counts:
        return 0

    max_counts = {}
    for reference in references:
        reference_counts = Counter(ngrams(reference, n))
        for ngram in counts:
            max_counts[ngram] = max(max_counts.get(ngram, 0), reference_counts[ngram])

    clipped_counts = dict((ngram, min(count, max_counts[ngram])) for ngram, count in counts.items())

    return sum(clipped_counts.values()) / sum(counts.values())


def _brevity_penalty(candidate, references):
    """Calculate brevity penalty.

    As the modified n-gram precision still has the problem from the short
    length sentence, brevity penalty is used to modify the overall BLEU
    score according to length.

    An example from the paper. There are three references with length 12, 15
    and 17. And a terse candidate of the length 12. The brevity penalty is 1.

    >>> references = [['a'] * 12, ['a'] * 15, ['a'] * 17]
    >>> candidate = ['a'] * 12
    >>> _brevity_penalty(candidate, references)
    1.0

    In case a candidate translation is shorter than the references, penalty is
    applied.

    >>> references = [['a'] * 28, ['a'] * 28]
    >>> candidate = ['a'] * 12
    >>> _brevity_penalty(candidate, references)
    0.2635...

    The length of the closest reference is used to compute the penalty. If the
    length of a candidate is 12, and the reference lengths are 13 and 2, the
    penalty is applied because the candidate length (12) is less then the
    closest reference length (13).

    >>> references = [['a'] * 13, ['a'] * 2]
    >>> candidate = ['a'] * 12
    >>> _brevity_penalty(candidate, references)
    0.92...

    The brevity penalty doesn't depend on reference order. More importantly,
    when two reference sentences are at the same distance, the shortest
    reference sentence length is used.

    >>> references = [['a'] * 13, ['a'] * 11]
    >>> candidate = ['a'] * 12
    >>> _brevity_penalty(candidate, references) == _brevity_penalty(candidate, reversed(references)) == 1
    True

    A test example from mteval-v13a.pl (starting from the line 705):

    >>> references = [['a'] * 11, ['a'] * 8]
    >>> candidate = ['a'] * 7
    >>> _brevity_penalty(candidate, references)
    0.86...

    >>> references = [['a'] * 11, ['a'] * 8, ['a'] * 6, ['a'] * 7]
    >>> candidate = ['a'] * 7
    >>> _brevity_penalty(candidate, references)
    1.0

    """
    c = len(candidate)
    ref_lens = (len(reference) for reference in references)
    r = min(ref_lens, key=lambda ref_len: (abs(ref_len - c), ref_len))

    if c > r:
        return 1
    else:
        return math.exp(1 - r / c)


# run doctests
if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
