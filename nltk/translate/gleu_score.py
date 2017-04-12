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

    Note: Unlike multi-reference BLEU, this implementation of GLEU only
          supports a single reference.

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

    :param reference: a reference sentence
    :type reference: list(str)
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: the sentence level GLEU score.
    :rtype: float
    """
    # For each order of ngram, calculate the no. of ngram matches and
    # keep track of no. of ngram in references.
    ref_ngrams = Counter(everygrams(reference, min_len, max_len))
    hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
    overlap_ngrams = ref_ngrams & hyp_ngrams
    tp = sum(overlap_ngrams.values()) # True positives.
    tpfp = sum(hyp_ngrams.values()) # True positives + False positives.
    tpfn = sum(ref_ngrams.values()) # True positives + False negatives.

    # While defined as the minimum of precision and recall, we can
    # reduce the number of division operations by one by instead finding
    # the maximum of the denominators for the precision and recall
    # formulae, since the numerators are the same:
    #     precision = tp / tpfp
    #     recall = tp / tpfn
    #     min(precision, recall) == tp / max(tpfp, tpfn)

    return tp / max(tpfp, tpfn)


def corpus_gleu(references, hypotheses, min_len=1, max_len=4):
    """
    Calculate a single corpus-level GLEU score (aka. system-level GLEU) for all
    the hypotheses and their respective references.

    Instead of averaging the sentence level GLEU scores (i.e. macro-average
    precision), Wu et al. (2016) sum up the matching tokens and the max of
    hypothesis and reference tokens for each sentence, then compute using the
    aggregate values.

    From Mike Schuster (via email):
        "For the corpus, we just add up the two statistics n_match and
         n_all = max(n_all_output, n_all_target) for all sentences, then
         calculate gleu_score = n_match / n_all, so it is not just a mean of
         the sentence gleu scores (in our case, longer sentences count more,
         which I think makes sense as they are more difficult to translate)."

    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2 = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> references = [ref1, ref2]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_gleu(references, hypotheses) # doctest: +ELLIPSIS
    0.5673...

    The example below show that corpus_gleu() is different from averaging
    sentence_gleu() for hypotheses

    >>> score1 = sentence_gleu(ref1, hyp1)
    >>> score2 = sentence_gleu(ref2, hyp2)
    >>> (score1 + score2) / 2 # doctest: +ELLIPSIS
    0.6144...

    :param references: a list of reference sentences, w.r.t. hypotheses
    :type references: list(list(str))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: The corpus-level GLEU score.
    :rtype: float
    """
    # sanity checks
    assert len(references) == len(hypotheses), "The number of hypotheses and references should be the same"
    assert len(references) > 0, "Cannot compute GLEU score for an empty corpus."
    # should the following use all()?
    assert any(len(ref) for ref in references), "At least one reference must be non-empty."

    # sum matches and max-token-lengths over all sentences
    n_match = 0
    n_all = 0

    for reference, hypothesis in zip(references, hypotheses):    
        ref_ngrams = Counter(everygrams(reference, min_len, max_len))
        hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
        overlap_ngrams = ref_ngrams & hyp_ngrams

        tp = sum(overlap_ngrams.values()) # True positives.
        tpfp = sum(hyp_ngrams.values()) # True positives + False positives.
        tpfn = sum(ref_ngrams.values()) # True positives + False negatives.

        n_match += tp
        n_all += max(tpfp, tpfn)

    return n_match / n_all
