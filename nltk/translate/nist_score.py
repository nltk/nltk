# -*- coding: utf-8 -*-
# Natural Language Toolkit: NIST Score
#
# Copyright (C) 2001-2017 NLTK Project
# Authors:
# Contributors:
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""NIST score implementation."""
from __future__ import division

import math
import fractions
from collections import Counter

from nltk.util import ngrams
from nltk.translate.bleu_score import modified_precision, closest_ref_length

try:
    fractions.Fraction(0, 1000, _normalize=False)
    from fractions import Fraction
except TypeError:
    from nltk.compat import Fraction


def sentence_nist(references, hypothesis, n=5):
    """
    Calculate NIST score from
    George Doddington. 2002. "Automatic evaluation of machine translation quality
    using n-gram co-occurrence statistics." Proceedings of HLT.
    Morgan Kaufmann Publishers Inc. http://dl.acm.org/citation.cfm?id=1289189.1289273

    DARPA commissioned NIST to develop an MT evaluation facility based on the BLEU
    score. The official script used by NIST to compute BLEU and NIST score is
    mteval-14.pl. The main differences are:

     - BLEU uses geometric mean of the ngram overlaps, NIST uses arithmetic mean.
     - NIST has a different brevity penalty
     - NIST score from mteval-14.pl has a self-contained tokenizer

    Note: The mteval-14.pl includes a smoothing function for BLEU score that is NOT
          used in the NIST score computation.

    >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...               'ensures', 'that', 'the', 'military', 'always',
    ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
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

    >>> sentence_nist([reference1, reference2, reference3], hypothesis1) # doctest: +ELLIPSIS
    0.0854...

    >>> sentence_nist([reference1, reference2, reference3], hypothesis2) # doctest: +ELLIPSIS
    0.1485...

    :param references: reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param n: highest n-gram order
    :type n: int
    """
    return corpus_nist([references], [hypothesis], n)

def corpus_nist(list_of_references, hypotheses, n=5):
    """
    Calculate a single corpus-level NIST score (aka. system-level BLEU) for all
    the hypotheses and their respective references.

    :param references: a corpus of lists of reference sentences, w.r.t. hypotheses
    :type references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param n: highest n-gram order
    :type n: int
    """
    # Before proceeding to compute NIST, perform sanity checks.
    assert len(list_of_references) == len(hypotheses), "The number of hypotheses and their reference(s) should be the same"

    p_numerators = Counter() # Key = ngram order, and value = no. of ngram matches.
    p_denominators = Counter() # Key = ngram order, and value = no. of ngram in ref.
    sysoutput_lengths = Counter() # Key = ngram order, and value = no. of ngram in hyp.
    hyp_lengths, ref_lengths = 0, 0

    # Iterate through each hypothesis and their corresponding references.
    for references, hypothesis in zip(list_of_references, hypotheses):
        # For each order of ngram, calculate the numerator and
        # denominator for the corpus-level modified precision.
        for i, _ in enumerate(range(1,n+1)):
            p_i = modified_precision(references, hypothesis, i)
            p_numerators[i] += p_i.numerator
            p_denominators[i] += p_i.denominator
            # Adds the no. of ngrams in the hypothesis.
            sysoutput_lengths[i] += len(hypothesis) - (i - 1)

        # Calculate the hypothesis length and the closest reference length.
        # Adds them to the corpus-level hypothesis and reference counts.
        hyp_len =  len(hypothesis)
        hyp_lengths += hyp_len
        ref_lengths += closest_ref_length(references, hyp_len)

    # Calculate corpus-level brevity penalty.
    bp = nist_length_penalty(ref_lengths, hyp_lengths)

    # Collects the various precision values for the different ngram orders.
    p_n = [Fraction(p_numerators[i], p_denominators[i], _normalize=False)
           for i, _ in enumerate(range(1,n+1))]

    # Eqn 2 in Doddington (2002):
    # Info(w_1 ... w_n) = log_2 [ (# of occurrences of w_1 ... w_n-1) / (# of occurrences of w_1 ... w_n) ]
    info = [0 if p_n[i].numerator == 0 or p_n[i+1].numerator == 0 # Handles math domain and zero division errors.
            else math.log(p_n[i].numerator / p_n[i+1].numerator)
            for i in range(len(p_n)-1)]
    return sum(info_i/sysoutput_lengths[i] for i, info_i in enumerate(info)) * bp


def nist_length_penalty(closest_ref_len, hyp_len):
    """
    Calculates the NIST length penalty, from Eq. 3 in Doddington (2002)

        penalty = exp( beta * log( min( len(hyp)/len(ref) , 1.0 )))

    where,

        `beta` is chosen to make the brevity penalty factor = 0.5 when the
        no. of words in the system output (hyp) is 2/3 of the average
        no. of words in the reference translation (ref)

    The NIST penalty is different from BLEU's such that it minimize the impact
    of the score of small variations in the length of a translation.
    See Fig. 4 in  Doddington (2002)
    """
    ratio = closest_ref_len / hyp_len
    if 0 < ratio < 1:
        ratio_x, score_x = 1.5, 0.5
        beta = math.log(score_x) / math.log(score_x)**2
        return math.exp(beta * math.log(ratio)**2)
    else: # ratio <= 0 or ratio >= 1
        return max(min(ratio, 1.0), 0.0)
