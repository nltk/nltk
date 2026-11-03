# Natural Language Toolkit: Word Error Rate
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Word error rate (WER) implementation."""

from nltk.metrics.distance import _check_distance_input_len, edit_distance
from nltk.translate.api import MetricI


def sentence_wer(references, hypothesis, *, on_empty="raise"):
    """
    Calculate the word error rate (WER) of a hypothesis: the number of words
    to substitute, delete or insert to turn the hypothesis into the
    reference, divided by the number of words of the reference. It is an
    error rate, so lower is better, and it exceeds 1 when the hypothesis is
    much longer than the reference.

    The words are Levenshtein's edit distance (Levenshtein, 1966) applied to
    words, as jiwer computes WER, and as speech recognition and machine
    translation have used it since Niessen et al. (2000), "An Evaluation Tool
    for Machine Translation: Fast Evaluation for MT Research", LREC.

    Two of the reference's six words are wrong in the hypothesis, one
    substituted ("cat" for "mat") and one deleted ("the"):

        >>> reference = 'the cat sat on the mat'.split()
        >>> hypothesis = 'the cat sat on cat'.split()
        >>> round(sentence_wer([reference], hypothesis), 4)
        0.3333

    With several references the hypothesis is scored against the one it is
    closest to, by the fewest edits (the first on a tie), and divided by that
    reference's length: the multi-reference WER, mWER, of Niessen et al.

        >>> other = 'on the mat sat the cat'.split()
        >>> round(sentence_wer([other, reference], hypothesis), 4)
        0.3333

    :param references: the references of the hypothesis
    :type references: list(list(str))
    :param hypothesis: a hypothesis
    :type hypothesis: list(str)
    :param on_empty: "raise" (the default) or "zero", for a hypothesis
        without references
    :type on_empty: str
    :rtype: float
    """
    return WER(on_empty=on_empty).sentence_score(references, hypothesis)


def corpus_wer(list_of_references, hypotheses, *, on_empty="raise"):
    """
    Calculate the word error rate of a corpus: the edits of all hypotheses
    divided by the words of all their references, so that a long sentence
    weighs more than a short one, as jiwer and sclite sum a corpus.

        >>> refs = [['the cat sat on the mat'.split()], ['thank you'.split()]]
        >>> hyps = ['the cat sat on cat'.split(), 'thanks you'.split()]
        >>> round(corpus_wer(refs, hyps), 4)
        0.375

    :param list_of_references: the references of each hypothesis
    :type list_of_references: list(list(list(str)))
    :param hypotheses: the hypotheses
    :type hypotheses: list(list(str))
    :param on_empty: "raise" (the default) or "zero", for an empty corpus or a
        hypothesis without references
    :type on_empty: str
    :rtype: float
    """
    return WER(on_empty=on_empty).corpus_score(list_of_references, hypotheses)


class WER(MetricI):
    """
    Word error rate in two modes. ``"nltk"`` is corpus_wer() and
    sentence_wer(): the fewest edits, Levenshtein's distance, as jiwer counts
    them. ``"sclite"`` counts the edits of the alignment that NIST's sclite
    (SCTK 2.4.12) makes, which weighs a substitution 4 and an insertion or a
    deletion 3 and so prefers a substitution to the two edits that replace
    it; on a tie it takes the substitution, then the deletion. That alignment
    can have more edits than the fewest. Five substitutions turn "b b c c c"
    into "a a a b b" and weigh 20; deleting the three "a" and inserting the
    three "c" around the matched "b b" weighs 18, so sclite counts six edits:

        >>> from nltk.translate.wer_score import WER
        >>> reference, hypothesis = 'a a a b b'.split(), 'b b c c c'.split()
        >>> WER().sentence_score([reference], hypothesis)
        1.0
        >>> WER(mode="sclite").sentence_score([reference], hypothesis)
        1.2

    sclite compares words without case unless it is run with -s; both modes
    compare the tokens as they are given, as sclite -s does. sclite's markup
    for references (optionally deleted words in parentheses, "@") is not
    read.

    :param mode: "nltk" or "sclite"
    :param on_empty: "raise" or "zero", see MetricI
    """

    modes = ("nltk", "sclite")

    def __init__(self, *, mode="nltk", on_empty="raise"):
        super().__init__(mode, on_empty)

    def _corpus_score(self, list_of_references, hypotheses):
        edits = words = 0
        count = edit_distance if self.mode == "nltk" else _sclite_edits
        for references, hypothesis in zip(list_of_references, hypotheses):
            # the closest reference, the first of those with the fewest edits
            best = min(
                (count(reference, hypothesis), len(reference))
                for reference in references
            )
            edits, words = edits + best[0], words + best[1]
        if words == 0:
            raise ValueError(
                "WER divides by the number of reference words, and the "
                "references have none"
            )
        return edits / words


def _sclite_edits(reference, hypothesis):
    """
    The substitutions, deletions and insertions of sclite's alignment of the
    hypothesis to the reference (net_dp.c in SCTK): the alignment of least
    weight, a substitution 4 and an insertion or deletion 3, which on a tie
    takes the substitution, then the deletion, then the insertion.
    """
    _check_distance_input_len(reference, hypothesis, "WER")
    # each cell is (weight, edits) of the best alignment of the prefixes
    previous = [(3 * j, j) for j in range(len(hypothesis) + 1)]
    for i, ref_word in enumerate(reference, 1):
        current = [(3 * i, i)]
        for j, hyp_word in enumerate(hypothesis, 1):
            same = ref_word == hyp_word
            substitute = (
                previous[j - 1][0] + (0 if same else 4),
                previous[j - 1][1] + (0 if same else 1),
            )
            delete = (previous[j][0] + 3, previous[j][1] + 1)
            insert = (current[j - 1][0] + 3, current[j - 1][1] + 1)
            if substitute[0] <= delete[0] and substitute[0] <= insert[0]:
                current.append(substitute)
            elif delete[0] < insert[0]:
                current.append(delete)
            else:
                current.append(insert)
        previous = current
    return previous[-1][1]
