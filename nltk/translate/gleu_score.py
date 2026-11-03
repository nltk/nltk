# Natural Language Toolkit: GLEU Score
#
# Copyright (C) 2001-2026 NLTK Project
# Authors:
# Contributors: Mike Schuster, Michael Wayne Goodman, Liling Tan
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""GLEU score implementation."""

from collections import Counter

from nltk.translate.api import MetricI, smooth_counts
from nltk.translate.chrf_score import _ngram_matches
from nltk.util import everygrams, ngrams


def sentence_gleu(
    references,
    hypothesis,
    min_len=1,
    max_len=4,
    *,
    smoothing=None,
    smooth_value=None,
    on_empty="raise",
):
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

    Note: The initial implementation only allowed a single reference, but now
          a list of references is required (which is consistent with
          bleu_score.sentence_bleu()).

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_gleu([ref], hyp)  # doctest: +ELLIPSIS
        0.0909...

    An example to evaluate normal machine translation outputs

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_gleu([ref1], hyp1) # doctest: +ELLIPSIS
        0.4393...
        >>> sentence_gleu([ref1], hyp2) # doctest: +ELLIPSIS
        0.1206...

    :param references: a list of reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param smoothing: None (no smoothing), "floor", "add-k" or "exp"; see
        nltk.translate.api.smooth_counts
    :type smoothing: str
    :param smooth_value: the floor or the k of the smoothing
    :type smooth_value: float
    :param on_empty: "raise" (the default) or "zero", for a hypothesis
        without references
    :type on_empty: str
    :return: the sentence level GLEU score.
    :rtype: float
    """
    return corpus_gleu(
        [references],
        [hypothesis],
        min_len=min_len,
        max_len=max_len,
        smoothing=smoothing,
        smooth_value=smooth_value,
        on_empty=on_empty,
    )


def corpus_gleu(
    list_of_references,
    hypotheses,
    min_len=1,
    max_len=4,
    *,
    smoothing=None,
    smooth_value=None,
    on_empty="raise",
):
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
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_gleu(list_of_references, hypotheses) # doctest: +ELLIPSIS
    0.5673...

    The example below show that corpus_gleu() is different from averaging
    sentence_gleu() for hypotheses

    >>> score1 = sentence_gleu([ref1a], hyp1)
    >>> score2 = sentence_gleu([ref2a], hyp2)
    >>> (score1 + score2) / 2 # doctest: +ELLIPSIS
    0.6144...

    :param list_of_references: a list of reference sentences, w.r.t. hypotheses
    :type list_of_references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param smoothing: None (no smoothing), "floor", "add-k" or "exp"; see
        nltk.translate.api.smooth_counts
    :type smoothing: str
    :param smooth_value: the floor or the k of the smoothing
    :type smooth_value: float
    :param on_empty: "raise" (the default) or "zero", for an empty corpus or a
        hypothesis without references
    :type on_empty: str
    :return: The corpus-level GLEU score.
    :rtype: float
    """
    return GLEU(
        min_len,
        max_len,
        smoothing=smoothing,
        smooth_value=smooth_value,
        on_empty=on_empty,
    ).corpus_score(list_of_references, hypotheses)


class GLEU(MetricI):
    """
    Google's GLEU, corpus_gleu() and sentence_gleu() as a metric. NLTK's is its
    only mode: neither mteval nor sacrebleu has GLEU.

    GLEU pools the n-grams of all its orders, so an order without matches does
    not zero it. It takes the smoothings of nltk.translate.api.smooth_counts,
    which smooth each order's matches and n-grams before they are pooled. The
    scrambled words below match as unigrams only; "exp" lets the bigrams,
    trigrams and 4-grams count 1/2, 1/4 and 1/8 of a match, 6.875 matches of
    the 18 n-grams:

        >>> from nltk.translate.gleu_score import GLEU
        >>> reference = 'the cat sat on the mat'.split()
        >>> scrambled = 'mat the on sat cat the'.split()
        >>> round(GLEU().sentence_score([reference], scrambled), 4)
        0.3333
        >>> round(GLEU(smoothing="exp").sentence_score([reference], scrambled), 4)
        0.3819

    :param min_len: lowest n-gram order
    :param max_len: highest n-gram order
    :param smoothing: None (no smoothing), "floor", "add-k" or "exp"
    :param smooth_value: the floor or the k of the smoothing
    :param on_empty: "raise" or "zero", see MetricI
    """

    def __init__(
        self,
        min_len=1,
        max_len=4,
        *,
        smoothing=None,
        smooth_value=None,
        mode="nltk",
        on_empty="raise",
    ):
        super().__init__(mode, on_empty)
        smoothing = smoothing or "none"
        smooth_counts([], smoothing)  # an unknown method raises ValueError
        self.min_len, self.max_len = min_len, max_len
        self.smoothing, self.smooth_value = smoothing, smooth_value

    def _corpus_score(self, list_of_references, hypotheses):
        if self.smoothing != "none":
            return _smoothed_corpus_gleu(
                list_of_references,
                hypotheses,
                range(self.min_len, self.max_len + 1),
                self.smoothing,
                self.smooth_value,
            )
        return _corpus_gleu(list_of_references, hypotheses, self.min_len, self.max_len)


def _smoothed_corpus_gleu(list_of_references, hypotheses, orders, smoothing, value):
    """
    _corpus_gleu() with each order's matches and n-grams smoothed (see
    nltk.translate.api.smooth_counts) before they are pooled: the pooled
    counts of all orders are those everygrams() gives.
    """
    corpus_n_match = corpus_n_all = 0
    for references, hypothesis in zip(list_of_references, hypotheses):
        hyp_counts = []
        for reference in references:
            counts = smooth_counts(
                [(n, *_ngram_matches(reference, hypothesis, n)) for n in orders],
                smoothing,
                value,
            )
            tp = sum(c[1] for c in counts)
            n_all = max(sum(c[2] for c in counts), sum(c[3] for c in counts))
            if n_all > 0:
                hyp_counts.append((tp, n_all))
        if hyp_counts:
            n_match, n_all = max(hyp_counts, key=lambda hc: hc[0] / hc[1])
            corpus_n_match += n_match
            corpus_n_all += n_all
    return corpus_n_match / corpus_n_all if corpus_n_all else 0.0


def _corpus_gleu(list_of_references, hypotheses, min_len, max_len):
    """corpus_gleu() of a corpus with hypotheses and references."""
    # sum matches and max-token-lengths over all sentences
    corpus_n_match = 0
    corpus_n_all = 0

    for references, hypothesis in zip(list_of_references, hypotheses):
        hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
        tpfp = sum(hyp_ngrams.values())  # True positives + False positives.

        hyp_counts = []
        for reference in references:
            ref_ngrams = Counter(everygrams(reference, min_len, max_len))
            tpfn = sum(ref_ngrams.values())  # True positives + False negatives.

            overlap_ngrams = ref_ngrams & hyp_ngrams
            tp = sum(overlap_ngrams.values())  # True positives.

            # While GLEU is defined as the minimum of precision and
            # recall, we can reduce the number of division operations by one by
            # instead finding the maximum of the denominators for the precision
            # and recall formulae, since the numerators are the same:
            #     precision = tp / tpfp
            #     recall = tp / tpfn
            #     gleu_score = min(precision, recall) == tp / max(tpfp, tpfn)
            n_all = max(tpfp, tpfn)

            if n_all > 0:
                hyp_counts.append((tp, n_all))

        # use the reference yielding the highest score
        if hyp_counts:
            n_match, n_all = max(hyp_counts, key=lambda hc: hc[0] / hc[1])
            corpus_n_match += n_match
            corpus_n_all += n_all

    # corner case: no hypothesis or reference has n-grams of these orders,
    # don't divide by zero
    if corpus_n_all == 0:
        gleu_score = 0.0
    else:
        gleu_score = corpus_n_match / corpus_n_all

    return gleu_score
