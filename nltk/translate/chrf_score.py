# -*- coding: utf-8 -*-
# Natural Language Toolkit: ChrF score
#
# Copyright (C) 2001-2017 NLTK Project
# Authors: Maja Popovic
# Contributors: Liling Tan
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

""" ChrF score implementation """
from __future__ import division
from collections import Counter

from nltk.util import ngrams, everygrams

def sentence_chrf(reference, hypothesis, min_len=1, max_len=6, beta=3.0):
    """
    Calculates the sentence level CHRF (Character n-gram F-score) described in
     - Maja Popovic. 2015. CHRF: Character n-gram F-score for Automatic MT Evaluation.
       In Proceedings of the 10th Workshop on Machine Translation.
       http://www.statmt.org/wmt15/pdf/WMT49.pdf
     - Maja Popovic. 2016. CHRF Deconstructed: β Parameters and n-gram Weights.
       In Proceedings of the 1st Conference on Machine Translation.
       http://www.statmt.org/wmt16/pdf/W16-2341.pdf

    Unlike multi-reference BLEU, CHRF only supports a single reference.

    An example from the original BLEU paper
    http://www.aclweb.org/anthology/P02-1040.pdf

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6768...
        >>> sentence_chrf(ref1, hyp2) # doctest: +ELLIPSIS
        0.4201...

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_chrf(ref, hyp)  # doctest: +ELLIPSIS
        0.2530...

    An example to show that this function allows users to use strings instead of
    tokens, i.e. list(str) as inputs.

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands')
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party')
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6768...
        >>> type(ref1) == type(hyp1) == str
        True
        >>> sentence_chrf(ref1.split(), hyp1.split()) # doctest: +ELLIPSIS
        0.6768...

    To skip the unigrams and only use 2- to 3-grams:

        >>> sentence_chrf(ref1, hyp1, min_len=2, max_len=3) # doctest: +ELLIPSIS
        0.7018...

    :param references: reference sentence
    :type references: list(str) / str
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str) / str
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param beta: the parameter to assign more importance to recall over precision
    :type beta: float
    :return: the sentence level CHRF score.
    :rtype: float
    """
    return corpus_chrf([reference], [hypothesis], min_len, max_len, beta=beta)


def corpus_chrf(list_of_references, hypotheses, min_len=1, max_len=6, beta=3.0):
    """
    Calculates the corpus level CHRF (Character n-gram F-score), it is the
    micro-averaged value of the sentence/segment level CHRF score.

    CHRF only supports a single reference.

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> ref2 = str('It is the guiding principle which guarantees the military '
        ...            'forces always being under the command of the Party').split()
        >>>
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct')
        >>> corpus_chrf([ref1, ref2, ref1, ref2], [hyp1, hyp2, hyp2, hyp1]) # doctest: +ELLIPSIS
        0.4915...

    :param references: a corpus of list of reference sentences, w.r.t. hypotheses
    :type references: list(list(str)) / list(str)
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str)) / list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param beta: the parameter to assign more importance to recall over precision
    :type beta: float
    :return: the sentence level CHRF score.
    :rtype: float
    """

    assert len(list_of_references) == len(hypotheses), "The number of hypotheses and their references should be the same"

    # Iterate through each hypothesis and their corresponding references.
    for reference, hypothesis in zip(list_of_references, hypotheses):
        # Cheating condition to allow users to input strings instead of tokens.
        if type(reference) and type(hypothesis) != str:
            reference, hypothesis = ' '.join(reference), ' '.join(hypothesis)
        # For each order of ngram, calculate the no. of ngram matches and
        # keep track of no. of ngram in references.
        ref_ngrams = Counter(everygrams(reference, min_len, max_len))
        hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
        overlap_ngrams = ref_ngrams & hyp_ngrams
        tp = sum(overlap_ngrams.values()) # True positives.
        tpfp = sum(hyp_ngrams.values()) # True positives + False positives.
        tffn = sum(ref_ngrams.values()) # True posities + False negatives.

    precision = tp / tpfp
    recall = tp / tffn
    factor = beta**2
    score = (1+ factor ) * (precision * recall) / ( factor * precision + recall)
    return score
