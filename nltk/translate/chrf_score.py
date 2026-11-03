# Natural Language Toolkit: ChrF score
#
# Copyright (C) 2001-2026 NLTK Project
# Authors: Maja Popovic
# Contributors: Liling Tan, Aleš Tamchyna (Memsource)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""ChrF score implementation"""

import string
from collections import Counter, defaultdict

from nltk import redos
from nltk.translate.api import MetricI
from nltk.util import ngrams


def sentence_chrf(
    reference,
    hypothesis,
    min_len=1,
    max_len=6,
    beta=3.0,
    ignore_whitespace=True,
    *,
    word_order=0,
    on_empty="raise",
):
    """
    Calculates the sentence level CHRF (Character n-gram F-score) described in
     - Maja Popovic. 2015. CHRF: Character n-gram F-score for Automatic MT Evaluation.
       In Proceedings of the 10th Workshop on Machine Translation.
       https://www.statmt.org/wmt15/pdf/WMT49.pdf
     - Maja Popovic. 2016. CHRF Deconstructed: β Parameters and n-gram Weights.
       In Proceedings of the 1st Conference on Machine Translation.
       https://www.statmt.org/wmt16/pdf/W16-2341.pdf

    This implementation of CHRF only supports a single reference at the moment.

    For details not reported in the paper, consult Maja Popovic's original
    implementation: https://github.com/m-popovic/chrF

    The code should output results equivalent to running CHRF++ with the
    following options: -nw 0 -b 3

    An example from the original BLEU paper
    https://www.aclweb.org/anthology/P02-1040.pdf

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6349...
        >>> sentence_chrf(ref1, hyp2) # doctest: +ELLIPSIS
        0.3330...

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_chrf(ref, hyp)  # doctest: +ELLIPSIS
        0.1468...

    An example to show that this function allows users to use strings instead of
    tokens, i.e. list(str) as inputs.

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands')
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party')
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6349...
        >>> type(ref1) == type(hyp1) == str
        True
        >>> sentence_chrf(ref1.split(), hyp1.split()) # doctest: +ELLIPSIS
        0.6349...

    To skip the unigrams and only use 2- to 3-grams:

        >>> sentence_chrf(ref1, hyp1, min_len=2, max_len=3) # doctest: +ELLIPSIS
        0.6617...

    chrF++ (Popovic, 2017) adds word n-grams to the character n-grams:
    ``word_order=2`` averages the F-scores of the word unigrams and bigrams
    with those of the six character orders. The words are the text split at
    whitespace, with a punctuation mark at the end or the start of a word
    split off, as chrF++.py does. Here the word unigrams (F 0.679) match
    better than the average character order (0.635) and the word bigrams
    (0.526) worse, so chrF++ ends a little below chrF:

        >>> sentence_chrf(ref1, hyp1, word_order=2) # doctest: +ELLIPSIS
        0.6269...

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
    :param ignore_whitespace: ignore whitespace characters in scoring
    :type ignore_whitespace: bool
    :param word_order: the highest word n-gram order, 0 for chrF and 2 for
        chrF++
    :type word_order: int
    :param on_empty: "raise" (the default) or "zero", as for the other
        metrics; one hypothesis with its reference is never an empty input
    :type on_empty: str
    :return: the sentence level CHRF score.
    :rtype: float
    """
    return corpus_chrf(
        [reference],
        [hypothesis],
        min_len,
        max_len,
        beta=beta,
        ignore_whitespace=ignore_whitespace,
        word_order=word_order,
        on_empty=on_empty,
    )


def _preprocess(sent, ignore_whitespace):
    if type(sent) != str:
        # turn list of tokens into a string
        sent = " ".join(sent)

    if ignore_whitespace:
        sent = redos.sub(r"\s+", "", sent)
    return sent


def _separate_punctuation(sent):
    """
    The words of chrF++: the text split at whitespace, and of a word longer
    than one character the punctuation mark at its end, or else at its start,
    split off, as chrF++.py (Popovic, 2017) and sacrebleu split them.

        >>> _separate_punctuation("Hello, (world)!")
        ['Hello', ',', '(world)', '!']
    """
    if not isinstance(sent, str):
        sent = " ".join(sent)
    words = []
    for word in sent.split():
        if len(word) > 1 and word[-1] in string.punctuation:
            words += [word[:-1], word[-1]]
        elif len(word) > 1 and word[0] in string.punctuation:
            words += [word[0], word[1:]]
        else:
            words.append(word)
    return words


def chrf_precision_recall_fscore_support(
    reference, hypothesis, n, beta=3.0, epsilon=1e-16
):
    """
    This function computes the precision, recall and fscore from the ngram
    overlaps. It returns the `support` which is the true positive score.

    By underspecifying the input type, the function will be agnostic as to how
    it computes the ngrams and simply take the whichever element in the list;
    it could be either token or character.

    :param reference: The reference sentence.
    :type reference: list
    :param hypothesis: The hypothesis sentence.
    :type hypothesis: list
    :param n: Extract up to the n-th order ngrams
    :type n: int
    :param beta: The parameter to assign more importance to recall over precision.
    :type beta: float
    :param epsilon: The fallback value if the hypothesis or reference is empty.
    :type epsilon: float
    :return: Returns the precision, recall and f-score and support (true positive).
    :rtype: tuple(float)
    """
    # True positives, true positives + false positives (the hypothesis
    # n-grams) and true positives + false negatives (the reference n-grams).
    tp, tpfp, tpfn = _ngram_matches(reference, hypothesis, n)

    try:
        prec = tp / tpfp  # precision
        rec = tp / tpfn  # recall
        factor = beta**2
        fscore = (1 + factor) * (prec * rec) / (factor * prec + rec)
    except ZeroDivisionError:
        prec = rec = fscore = epsilon
    return prec, rec, fscore, tp


def _ngram_matches(reference, hypothesis, n):
    """
    The n-grams of order n the hypothesis shares with the reference, each
    counted at most as often as the reference has it, and the numbers of
    hypothesis and of reference n-grams: what chrF, chrF++ and ROUGE-N divide.

        >>> _ngram_matches('the cat sat on the mat'.split(), 'the the the cat'.split(), 1)
        (3, 4, 6)
    """
    ref_ngrams = Counter(ngrams(reference, n))
    hyp_ngrams = Counter(ngrams(hypothesis, n))
    matches = sum((ref_ngrams & hyp_ngrams).values())
    return matches, sum(hyp_ngrams.values()), sum(ref_ngrams.values())


def corpus_chrf(
    references,
    hypotheses,
    min_len=1,
    max_len=6,
    beta=3.0,
    ignore_whitespace=True,
    *,
    word_order=0,
    on_empty="raise",
):
    """
    Calculates the corpus level CHRF (Character n-gram F-score), it is the
    macro-averaged value of the sentence/segment level CHRF score.

    This implementation of CHRF only supports a single reference at the moment.

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
        0.3910...

    :param references: a corpus of list of reference sentences, w.r.t. hypotheses
    :type references: list(list(str))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param beta: the parameter to assign more importance to recall over precision
    :type beta: float
    :param ignore_whitespace: ignore whitespace characters in scoring
    :type ignore_whitespace: bool
    :param word_order: the highest word n-gram order, 0 for chrF and 2 for
        chrF++; the corpus score of chrF++ is chrF++.py's "avgF" line
    :type word_order: int
    :param on_empty: "raise" (the default) or "zero", for an empty corpus
    :type on_empty: str
    :return: the sentence level CHRF score.
    :rtype: float
    """
    return CHRF(
        min_len,
        max_len,
        beta,
        ignore_whitespace,
        word_order=word_order,
        on_empty=on_empty,
    ).corpus_score([[reference] for reference in references], hypotheses)


def _corpus_chrf(
    references,
    hypotheses,
    min_len,
    max_len,
    beta,
    ignore_whitespace,
    word_order=0,
):
    """corpus_chrf() as NLTK computes it, CHRF's "nltk" mode."""
    num_sents = len(hypotheses)

    # Keep f-scores for each n-gram order separate
    ngram_fscores = defaultdict(list)

    # Iterate through each hypothesis and their corresponding references.
    for reference, hypothesis in zip(references, hypotheses):
        # chrF++: the word n-gram orders are averaged with the character ones
        ref_words = _separate_punctuation(reference)
        hyp_words = _separate_punctuation(hypothesis)
        for n in range(1, word_order + 1):
            fscore = chrf_precision_recall_fscore_support(
                ref_words, hyp_words, n, beta=beta
            )[2]
            ngram_fscores["word", n].append(fscore)

        # preprocess both reference and hypothesis
        reference = _preprocess(reference, ignore_whitespace)
        hypothesis = _preprocess(hypothesis, ignore_whitespace)

        # Calculate f-scores for each sentence and for each n-gram order
        # separately.
        for n in range(min_len, max_len + 1):
            # Compute the precision, recall, fscore and support.
            prec, rec, fscore, tp = chrf_precision_recall_fscore_support(
                reference, hypothesis, n, beta=beta
            )
            ngram_fscores[n].append(fscore)

    # how many n-gram sizes
    num_ngram_sizes = len(ngram_fscores)

    # sum of f-scores over all sentences for each n-gram order
    total_scores = [sum(fscores) for n, fscores in ngram_fscores.items()]

    # macro-average over n-gram orders and over all sentences
    return (sum(total_scores) / num_ngram_sizes) / num_sents


class CHRF(MetricI):
    """
    chrF in two modes. ``"nltk"`` is corpus_chrf() and sentence_chrf(): one
    reference per hypothesis, the F-score of each character n-gram order
    averaged over the orders, and a corpus score that averages the sentence
    scores. ``"sacrebleu"`` is sacrebleu's CHRF (sacrebleu 2.6.0):
    character n-grams from 1 to ``max_len``, the best reference of
    each hypothesis, and a corpus score from the statistics of all sentences.

    A sentence in both modes, with the same beta and sacrebleu's "eps"
    smoothing, gets the same score. The two corpus scores differ:

        >>> from nltk.translate.chrf_score import CHRF
        >>> hyps = ['the cat sat on the mat today'.split(), 'a dog is in the park now'.split()]
        >>> refs = [['the cat sat on the red mat today'.split()], ['the dog was in a park'.split()]]
        >>> round(CHRF().corpus_score(refs, hyps), 4)
        0.5414
        >>> round(CHRF(beta=3, smoothing="eps", mode="sacrebleu").corpus_score(refs, hyps), 4)
        0.5957
        >>> round(CHRF(mode="sacrebleu").corpus_score(refs, hyps), 4)
        0.5974

    chrF++ (Popovic, 2017) is chrF with word n-grams, ``word_order=2``: the
    word unigrams and bigrams are two more orders, averaged with the six
    character orders. Both modes split the words as chrF++.py does (see
    _separate_punctuation). A sentence in the nltk mode gets chrF++.py's
    sentence score, and a corpus its "avgF" line, the mean of the sentence
    scores; the sacrebleu mode is sacrebleu's CHRF(word_order=2), whose corpus
    score with "eps" is chrF++.py's other line, from the summed statistics.

        >>> round(CHRF(word_order=2).corpus_score(refs, hyps), 4)
        0.5579
        >>> round(CHRF(word_order=2, mode="sacrebleu").corpus_score(refs, hyps), 4)
        0.6073

    :param min_len: lowest character n-gram order; 1 in the sacrebleu mode
    :param max_len: highest character n-gram order
    :param beta: weight of recall over precision: 3.0 in the nltk mode, 2 in
        the sacrebleu mode, by default
    :param ignore_whitespace: leave the whitespace out of the character n-grams
    :param smoothing: what an order a hypothesis or reference has no n-grams
        of contributes: "eps" averages the F-scores of the orders, a missing
        one 1e-16 (the nltk mode, and sacrebleu's eps_smoothing); in the
        sacrebleu mode "effective-order" (its default) averages precision and
        recall over the orders both have
    :param word_order: highest word n-gram order: 0 for chrF, 2 for chrF++
    :param mode: "nltk" or "sacrebleu"
    :param on_empty: "raise" or "zero", see MetricI
    """

    modes = ("nltk", "sacrebleu")

    def __init__(
        self,
        min_len=1,
        max_len=6,
        beta=None,
        ignore_whitespace=True,
        smoothing=None,
        *,
        word_order=0,
        mode="nltk",
        on_empty="raise",
    ):
        super().__init__(mode, on_empty)
        if min_len > max_len:
            raise ValueError("min_len must be less than or equal to max_len")
        if mode == "nltk":
            if smoothing not in (None, "eps"):
                raise ValueError(f'the nltk mode smooths with "eps", not {smoothing!r}')
            beta = 3.0 if beta is None else beta
        else:
            if min_len != 1:
                raise ValueError(
                    "sacrebleu counts character n-grams from 1, so min_len is 1"
                )
            if smoothing not in (None, "effective-order", "eps"):
                raise ValueError(
                    f'the sacrebleu mode smooths with "effective-order" or "eps", not {smoothing!r}'
                )
            beta = 2 if beta is None else beta
            smoothing = smoothing or "effective-order"
        self.min_len, self.max_len, self.beta = min_len, max_len, beta
        self.ignore_whitespace, self.smoothing = ignore_whitespace, smoothing
        self.word_order = word_order

    def _corpus_score(self, list_of_references, hypotheses):
        if self.mode == "sacrebleu":
            return _sacrebleu_corpus_chrf(
                list_of_references,
                hypotheses,
                self.max_len,
                self.beta,
                self.ignore_whitespace,
                self.smoothing == "eps",
                self.word_order,
            )
        if any(len(references) != 1 for references in list_of_references):
            raise ValueError(
                "the nltk mode of chrF takes one reference per hypothesis; "
                'mode="sacrebleu" takes several'
            )
        return _corpus_chrf(
            [references[0] for references in list_of_references],
            hypotheses,
            self.min_len,
            self.max_len,
            self.beta,
            self.ignore_whitespace,
            self.word_order,
        )


def _sacrebleu_ngrams(sent, max_order, ignore_whitespace, word_order):
    """
    sacrebleu's extract_all_char_ngrams and, for chrF++, its word n-grams
    (extract_word_ngrams), on a string or a list of tokens.
    """
    words = _separate_punctuation(sent)
    return _sacrebleu_char_ngrams(sent, max_order, ignore_whitespace) + [
        Counter(ngrams(words, n)) for n in range(1, word_order + 1)
    ]


def _sacrebleu_char_ngrams(sent, max_order, ignore_whitespace):
    """sacrebleu's extract_all_char_ngrams, on a string or a list of tokens."""
    if not isinstance(sent, str):
        sent = " ".join(sent)
    if ignore_whitespace:
        sent = "".join(sent.split())
    return [
        Counter(sent[i : i + n] for i in range(len(sent) - n + 1))
        for n in range(1, max_order + 1)
    ]


def _sacrebleu_chrf_fscore(statistics, max_order, beta, eps_smoothing):
    """sacrebleu's CHRF._compute_f_score, on the 0 to 1 scale."""
    eps = 1e-16
    score = 0.0
    effective_order = 0
    factor = beta**2
    avg_prec, avg_rec = 0.0, 0.0
    for i in range(max_order):
        n_hyp, n_ref, n_match = statistics[3 * i : 3 * i + 3]
        prec = n_match / n_hyp if n_hyp > 0 else eps
        rec = n_match / n_ref if n_ref > 0 else eps
        denom = factor * prec + rec
        score += ((1 + factor) * prec * rec / denom) if denom > 0 else eps
        if n_hyp > 0 and n_ref > 0:
            avg_prec += prec
            avg_rec += rec
            effective_order += 1
    if eps_smoothing:
        return score / max_order
    if effective_order == 0:
        avg_prec = avg_rec = 0.0
    else:
        avg_prec /= effective_order
        avg_rec /= effective_order
    if avg_prec + avg_rec:
        score = (1 + factor) * avg_prec * avg_rec
        return score / ((factor * avg_prec) + avg_rec)
    return 0.0


def _sacrebleu_corpus_chrf(
    list_of_references,
    hypotheses,
    max_order,
    beta,
    ignore_whitespace,
    eps_smoothing,
    word_order=0,
):
    """
    chrF as sacrebleu computes it: for each hypothesis the statistics
    (hypothesis, reference and matched n-grams of every order) of the reference
    with the best F-score, summed over the corpus, then one F-score. An order
    the reference has no n-grams of counts no hypothesis n-grams either. The
    word orders of chrF++ follow the character orders.
    """
    orders = max_order + word_order
    totals = [0] * (3 * orders)
    for references, hypothesis in zip(list_of_references, hypotheses):
        hyp_ngrams = _sacrebleu_ngrams(
            hypothesis, max_order, ignore_whitespace, word_order
        )
        best_stats, best_fscore = [], -1.0
        for reference in references:
            stats = []
            for hyp, ref in zip(
                hyp_ngrams,
                _sacrebleu_ngrams(reference, max_order, ignore_whitespace, word_order),
            ):
                matches = sum((hyp & ref).values())
                stats += [sum(hyp.values()) if ref else 0, sum(ref.values()), matches]
            fscore = _sacrebleu_chrf_fscore(stats, orders, beta, eps_smoothing)
            if fscore > best_fscore:
                best_stats, best_fscore = stats, fscore
        totals = [a + b for a, b in zip(totals, best_stats)]
    return _sacrebleu_chrf_fscore(totals, orders, beta, eps_smoothing)
