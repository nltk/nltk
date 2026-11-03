# Natural Language Toolkit: ROUGE
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""ROUGE score implementation."""

from nltk.metrics.distance import _check_distance_input_len
from nltk.translate.api import MetricI, _refuse_smoothing
from nltk.translate.chrf_score import _ngram_matches


def sentence_rouge(references, hypothesis, variant=1, measure="f", *, on_empty="raise"):
    """
    Calculate ROUGE (Recall-Oriented Understudy for Gisting Evaluation) from

    Chin-Yew Lin. 2004. ROUGE: A Package for Automatic Evaluation of
    Summaries. In Text Summarization Branches Out, ACL Workshop.
    https://aclanthology.org/W04-1013.pdf

    ROUGE-N counts the n-grams the hypothesis shares with a reference, each
    at most as often as the reference has it: recall divides them by the
    reference's n-grams, precision by the hypothesis', and the F-score is
    their harmonic mean. ROUGE-L does the same with the longest common
    subsequence, the words both have in the same order, not necessarily
    next to each other.

    "was" replaces "sat": five of the six words match, three of the five
    bigrams, and "the cat on the mat" is the longest common subsequence.

        >>> reference = 'the cat sat on the mat'.split()
        >>> hypothesis = 'the cat was on the mat'.split()
        >>> round(sentence_rouge([reference], hypothesis), 4)
        0.8333
        >>> round(sentence_rouge([reference], hypothesis, variant=2), 4)
        0.6
        >>> round(sentence_rouge([reference], hypothesis, variant="L"), 4)
        0.8333

    Recall is what ROUGE was made for: of a long hypothesis that contains the
    whole reference, recall is perfect and precision is not.

        >>> longer = 'the cat sat on the mat and looked at the dog'.split()
        >>> sentence_rouge([reference], longer, measure="recall")
        1.0
        >>> round(sentence_rouge([reference], longer, measure="precision"), 4)
        0.5455

    With several references, the hypothesis keeps the reference with the
    best F-score, as Lin (2004, eq. 2) and rouge-score do; ROUGE(mode=
    "rouge-1.5.5") pools the references as ROUGE-1.5.5.pl does by default.

    :param references: the references of the hypothesis
    :type references: list(list(str))
    :param hypothesis: a hypothesis
    :type hypothesis: list(str)
    :param variant: the n-gram order of ROUGE-N (1, 2, ...), or "L" for ROUGE-L
    :type variant: int or str
    :param measure: "f" (the default), "precision" or "recall"
    :type measure: str
    :param on_empty: "raise" (the default) or "zero", for a hypothesis
        without references
    :type on_empty: str
    :rtype: float
    """
    return ROUGE(variant, measure, on_empty=on_empty).sentence_score(
        references, hypothesis
    )


def corpus_rouge(
    list_of_references, hypotheses, variant=1, measure="f", *, on_empty="raise"
):
    """
    Calculate the ROUGE of a corpus, the mean of the sentence scores, as
    rouge-score's scores are averaged and as ROUGE-1.5.5.pl averages its
    evaluations.

        >>> refs = [['the cat sat on the mat'.split()], ['thank you'.split()]]
        >>> hyps = ['the cat was on the mat'.split(), 'thank you very much'.split()]
        >>> round(corpus_rouge(refs, hyps), 4)
        0.75

    :param list_of_references: the references of each hypothesis
    :type list_of_references: list(list(list(str)))
    :param hypotheses: the hypotheses
    :type hypotheses: list(list(str))
    :param variant: the n-gram order of ROUGE-N (1, 2, ...), or "L" for ROUGE-L
    :type variant: int or str
    :param measure: "f" (the default), "precision" or "recall"
    :type measure: str
    :param on_empty: "raise" (the default) or "zero", for an empty corpus or a
        hypothesis without references
    :type on_empty: str
    :rtype: float
    """
    return ROUGE(variant, measure, on_empty=on_empty).corpus_score(
        list_of_references, hypotheses
    )


class ROUGE(MetricI):
    """
    ROUGE-N and ROUGE-L in two modes, which differ only for a hypothesis with
    several references. ``"nltk"`` is corpus_rouge() and sentence_rouge(): the
    reference with the best F-score, the first on a tie (Lin, 2004, eq. 2, and
    rouge-score 0.1.2's score_multi). ``"rouge-1.5.5"`` pools the matches and
    the n-grams of all the references before dividing, ROUGE-1.5.5.pl's
    default "-f A", and its F-score with "-p 0.5". A corpus is the mean of
    its sentences in both.

        >>> from nltk.translate.rouge_score import ROUGE
        >>> refs = ['the cat sat on the mat'.split(), 'a cat was sitting on a mat'.split()]
        >>> hyp = 'the cat was on the mat'.split()
        >>> round(ROUGE().sentence_score(refs, hyp), 4)
        0.8333
        >>> round(ROUGE(mode="rouge-1.5.5").sentence_score(refs, hyp), 4)
        0.72

    The second reference shares four words: pooled, 9 of the 13 reference
    words and 9 of the 12 hypothesis words (counted once per reference)
    match, a recall of 0.6923 and a precision of 0.75.

    Both take the tokens as they are given. rouge-score and ROUGE-1.5.5.pl
    tokenize themselves, lowercasing and keeping only ASCII letters and
    digits, so their scores of text in other scripts are near zero; give
    them the same tokens (ROUGE-1.5.5.pl as ASCII ids) and they agree with
    these modes. ROUGE-1.5.5.pl prints an average estimated from bootstrap
    samples and rounds to five decimals.

    :param variant: the n-gram order of ROUGE-N (1, 2, ...), or "L" for ROUGE-L
    :param measure: "f" (the default), "precision" or "recall"
    :param mode: "nltk" or "rouge-1.5.5"
    :param smoothing: "none" only (see MetricI)
    :param on_empty: "raise" or "zero", see MetricI
    """

    modes = ("nltk", "rouge-1.5.5")

    def __init__(
        self, variant=1, measure="f", *, smoothing=None, mode="nltk", on_empty="raise"
    ):
        super().__init__(mode, on_empty)
        _refuse_smoothing(
            self,
            smoothing,
            "scores one granularity, an n-gram order or the LCS, which no other order can make up for",
        )
        self.variant, self.measure = variant, measure

    def _corpus_score(self, list_of_references, hypotheses):
        index = {"precision": 0, "recall": 1, "f": 2}[self.measure]
        total = 0.0
        for references, hypothesis in zip(list_of_references, hypotheses):
            counts = [
                _rouge_counts(reference, hypothesis, self.variant)
                for reference in references
            ]
            if self.mode == "nltk":
                scores = max((_rouge_fscore(*c) for c in counts), key=lambda s: s[2])
            else:
                scores = _rouge155_fscore(*(sum(column) for column in zip(*counts)))
            total += scores[index]
        return total / len(hypotheses)


def _rouge_counts(reference, hypothesis, variant):
    """The matches, hypothesis length and reference length that ROUGE divides."""
    if variant == "L":
        return _lcs_length(reference, hypothesis), len(hypothesis), len(reference)
    return _ngram_matches(reference, hypothesis, variant)


def _rouge_fscore(matches, hyp_count, ref_count):
    """Precision, recall and F-score as rouge-score computes them."""
    precision = matches / hyp_count if hyp_count > 0 else 0.0
    recall = matches / ref_count if ref_count > 0 else 0.0
    if precision + recall > 0:
        return precision, recall, 2 * precision * recall / (precision + recall)
    return precision, recall, 0.0


def _rouge155_fscore(matches, hyp_count, ref_count, alpha=0.5):
    """Precision, recall and F-score as ROUGE-1.5.5.pl computes them, with -p alpha."""
    precision = matches / hyp_count if hyp_count != 0 else 0.0
    recall = matches / ref_count if ref_count != 0 else 0.0
    denominator = (1 - alpha) * precision + alpha * recall
    if denominator > 0:
        return precision, recall, (precision * recall) / denominator
    return precision, recall, 0.0


def _lcs_length(reference, hypothesis):
    """The length of the longest common subsequence of two token lists."""
    # quadratic in the lengths, so the inputs are bounded like edit_distance's
    _check_distance_input_len(reference, hypothesis, "ROUGE-L")
    previous = [0] * (len(hypothesis) + 1)
    for ref_token in reference:
        current = [0]
        for j, hyp_token in enumerate(hypothesis):
            if ref_token == hyp_token:
                current.append(previous[j] + 1)
            else:
                current.append(max(previous[j + 1], current[j]))
        previous = current
    return previous[-1]
