# -*- coding: utf-8 -*-
# Natural Language Toolkit: GLEU Score
#
# Copyright (C) 2001-2017 NLTK Project
# Authors:
# Contributors:
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

""" GLEU score implementation. """
from __future__ import division
from collections import Counter

from nltk.util import ngrams, everygrams

def sentence_gleu(reference, hypothesis, min_len=1, max_len=4):
    """
    Calculates the sentence level GLEU (Google-BLEU) score described in

        Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V. Le, Mohammad Norouzi,
        Wolfgang Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Klaus Macherey,
        Jeff Klingner, Apurva Shah, Melvin Johnson, Xiaobing Liu, Lukasz Kaiser,
        Stephan Gouws, Yoshikiyo Kato, Taku Kudo, Hideto Kazawa, Keith Stevens,
        George Kurian, Nishant Patil, Wei Wang, Cliff Young, Jason Smith,
        Jason Riesa, Alex Rudnick, Oriol Vinyals, Greg Corrado, Macduff Hughes,
        Jeffrey Dean. (2016) Google’s Neural Machine Translation System:
        Bridging the Gap between Human and Machine Translation.
        eprint arXiv:1609.08144. https://arxiv.org/pdf/1609.08144v2.pdf
        Retrieved on 27 Oct 2016.

    From Wu et al. (2016):
        "The BLEU score has some undesirable properties when used for single
         sentences, as it was designed to be a corpus measure. We therefore
         use a slightly different score for our RL experiments which we call
         the 'GLEU score'. For the GLEU score, we record all sub-sequences of
         1, 2, 3 or 4 tokens in output and target sequence (n-grams). We then
         compute a recall, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the target (ground truth) sequence,
         and a precision, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the generated output sequence. Then
         GLEU score is simply the minimum of recall and precision. This GLEU
         score's range is always between 0 (no matches) and 1 (all match) and
         it is symmetrical when switching output and target. According to
         our experiments, GLEU score correlates quite well with the BLEU
         metric on a corpus level but does not have its drawbacks for our per
         sentence reward objective."

    Note: The GLEU score is designed for sentence based evaluation thus there is
          no corpus based scores implemented in NLTK.

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_gleu(ref, hyp)  # doctest: +ELLIPSIS
        0.0909...

    An example to evaluate normal machine translation outputs

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_gleu(ref1, hyp1) # doctest: +ELLIPSIS
        0.4393...
        >>> sentence_gleu(ref1, hyp2) # doctest: +ELLIPSIS
        0.1206...

    :param references: reference sentence
    :type references: list(str)
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: the sentence level CHRF score.
    :rtype: float
    """
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

    return min(precision, recall)
