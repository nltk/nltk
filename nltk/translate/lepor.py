# Natural Language Toolkit: LEPOR Score
#
# Copyright (C) 2001-2023 NLTK Project
# Author: Ikram Ul Haq (ulhaqi12)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""LEPOR score implementation."""

import math
import re
import sys
from typing import Callable, List

import nltk


def length_penalty(reference: List[str], hypothesis: List[str]) -> float:
    """
    This function calculates the length penalty(LP) for the LEPOR metric, which is defined to embrace the penaltyvfor
    both longer and shorter hypothesis compared with the reference translations.
    Refer from Eq (2) on https://aclanthology.org/C12-2044

    :param reference: Reference sentence
    :type reference: str
    :param hypothesis: Hypothesis sentence
    :type hypothesis: str

    :return: Penalty of difference in length in reference and hypothesis sentence.
    :rtype: float
    """

    ref_len = len(reference)
    hyp_len = len(hypothesis)

    if ref_len == hyp_len:
        return 1
    elif ref_len < hyp_len:
        return math.exp(1 - (ref_len / hyp_len))
    else:  # i.e. r_len > hyp_len
        return math.exp(1 - (hyp_len / ref_len))


def alignment(ref_tokens: List[str], hyp_tokens: List[str]):
    """
    This function computes the context-dependent n-gram word alignment tasks that
    takes into account the surrounding context (neighbouring words) of the potential
    word to select a better matching pairs between the output and the reference.

    This alignment task is used to compute the ngram positional difference penalty
    component of the LEPOR score. Generally, the function finds the matching tokens
    between the reference and hypothesis, then find the indices of longest matching
    n-grams by checking the left and right unigram window of the matching tokens.

    :param ref_tokens: A list of tokens in reference sentence.
    :type ref_tokens: List[str]
    :param hyp_tokens: A list of tokens in hypothesis sentence.
    :type hyp_tokens: List[str]
    """
    alignments = []

    # Store the reference and hypothesis tokens length.
    hyp_len = len(hyp_tokens)
    ref_len = len(ref_tokens)

    for hyp_index, hyp_token in enumerate(hyp_tokens):

        # If no match.
        if ref_tokens.count(hyp_token) == 0:
            alignments.append(-1)
        # If only one match.
        elif ref_tokens.count(hyp_token) == 1:
            alignments.append(ref_tokens.index(hyp_token))
        # Otherwise, compute the multiple possibilities.
        else:
            # Keeps an index of where the hypothesis token matches the reference.
            ref_indexes = [
                i for i, ref_token in enumerate(ref_tokens) if ref_token == hyp_token
            ]

            # Iterate through the matched tokens, and check if
            # the one token to the left/right also matches.
            is_matched = []
            for ind, ref_index in enumerate(ref_indexes):
                # The one to the left token also matches.
                if (
                    0 < ref_index - 1 < ref_len
                    and 0 < hyp_index - 1 < hyp_len
                    and ref_tokens[ref_index - 1] == hyp_tokens[hyp_index - 1]
                ):
                    is_matched[ind] = True
                # The one to the right token also matches.
                elif (
                    0 < ref_index + 1 < ref_len
                    and 0 < hyp_index + 1 < hyp_len
                    and ref_tokens[ref_index + 1] == hyp_tokens[hyp_index + 1]
                ):
                    is_matched[ind] = True
                # If the left and right tokens don't match.
                else:
                    is_matched[ind] = False

            # Stores the alignments that have matching phrases.
            # If there's only a single matched alignment.
            if is_matched.count(True) == 1:
                alignments.append(ref_indexes[is_matched.index(True)])
            # If there's multiple matched alignments that have matching
            # tokens in the left/right window, we shift the index of the
            # alignment to the right most matching token.
            elif is_matched.count(True) > 1:
                min_distance = 0
                min_index = 0
                for match, ref_index in zip(is_matched, ref_indexes):
                    if match:
                        distance = abs(hyp_index - ref_index)
                        if distance > min_distance:
                            min_distance = distance
                            min_index = ref_index
                alignments.append(min_index)
            # If there's no matched alignments,
            # we still keep indexes of the matching tokens
            # without explicitly checking for the left/right window.
            else:
                min_distance = 0
                min_index = 0
                for ref_index in ref_indexes:
                    distance = abs(hyp_index - ref_index)
                    if distance > min_distance:
                        min_distance = distance
                        min_index = ref_index
                alignments.append(min_index)

                for ref_index in ref_indexes:
                    distance = abs(hyp_index - ref_index)
                    if distance > min_distance:
                        min_distance = distance
                        min_index = ref_index
                alignments.append(min_index)

    # The alignments are one indexed to keep track of the ending slice pointer of the matching ngrams.
    alignments = [a + 1 for a in alignments if a != -1]
    return alignments


def ngram_positional_penalty(
    ref_tokens: List[str], hyp_tokens: List[str]
) -> (float, float):
    """
    This function calculates the n-gram position difference penalty (NPosPenal) described in the LEPOR paper.
    The NPosPenal is an exponential of the length normalized n-gram matches between the reference and the hypothesis.

    :param ref_tokens: A list of words in reference sentence.
    :type ref_tokens: List[str]
    :param hyp_tokens: A list of words in hypothesis sentence.
    :type hyp_tokens: List[str]

    :return: A tuple containing two elements:
             - NPosPenal: N-gram positional penalty.
             - match_count: Count of matched n-grams.
    :rtype: tuple
    """

    alignments = alignment(ref_tokens, hyp_tokens)
    match_count = len(alignments)

    # Stores the n-gram position values (difference values) of aligned words
    # between output and reference sentences,
    # aka |PD| of eq (4) in https://aclanthology.org/C12-2044
    pd = []
    for i, a in enumerate(alignments):
        pd.append(abs((i + 1) / len(hyp_tokens) - a / len(ref_tokens)))

    npd = sum(pd) / len(hyp_tokens)
    return math.exp(-npd), match_count


def harmonic(
    match_count: int,
    reference_length: int,
    hypothesis_length: int,
    alpha: float,
    beta: float,
) -> float:
    """
    Function will calculate the precision and recall of matched words and calculate a final score on wighting
    using alpha and beta parameters.

    :param match_count: Number of words in hypothesis aligned with reference.
    :type match_count: int
    :param reference_length: Length of the reference sentence
    :type reference_length: int
    :param hypothesis_length: Length of the hypothesis sentence
    :type hypothesis_length: int
    :param alpha: A parameter to set weight fot recall.
    :type alpha: float
    :param beta: A parameter to set weight fot precision.
    :type beta: float

    :return: Harmonic mean.
    :rtype: float
    """

    epsilon = sys.float_info.epsilon

    precision = match_count / hypothesis_length
    recall = match_count / reference_length

    harmonic_score = (alpha + beta) / (
        (alpha / (recall + epsilon)) + (beta / (precision + epsilon))
    )

    return harmonic_score


def sentence_lepor(
    references: List[str],
    hypothesis: str,
    alpha: float = 1.0,
    beta: float = 1.0,
    tokenizer: Callable[[str], List[str]] = None,
) -> List[float]:
    """
    Calculate LEPOR score a sentence from Han, A. L.-F. (2017).
    LEPOR: An Augmented Machine Translation Evaluation Metric. https://arxiv.org/abs/1703.08748v2

    >>> hypothesis = 'a bird is on a stone.'

    >>> reference1 = 'a bird behind the stone.'
    >>> reference2 = 'a bird is on the rock.'

    >>> sentence_lepor([reference1, reference2], hypothesis)
    [0.7824248013113159, 0.7739937377760259]

    :param references: Reference sentences
    :type references: list(str)
    :param hypothesis: Hypothesis sentence
    :type hypothesis: str
    :param alpha: A parameter to set weight fot recall.
    :type alpha: float
    :param beta: A parameter to set weight fot precision.
    :type beta: float
    :param tokenizer: A callable tokenizer that will accept a string and returns a list of tokens.
    :type tokenizer: Callable[[str], List[str]]

    :return: The list of Lepor scores for a hypothesis with all references.
    :rtype: list(float)

    """

    lepor_scores = list()

    # Tokenize sentences.
    if tokenizer:
        hypothesis = tokenizer(hypothesis)
        for index, reference in enumerate(references):
            references[index] = tokenizer(reference)

    else:  # If tokenizer is not provided, use the one in NLTK.
        hypothesis = nltk.word_tokenize(hypothesis)
        for index, reference in enumerate(references):
            references[index] = nltk.word_tokenize(reference)

    for reference in references:
        if len(reference) == 0 or len(hypothesis) == 0:
            raise ValueError("One of the sentence is empty. Exit.")

        # Calculate the length penalty due to the difference in the length of reference and hypothesis.
        lp = length_penalty(reference, hypothesis)

        # Calculate the penalty on different positions of same word in translation.
        npd, match_count = ngram_positional_penalty(reference, hypothesis)

        harmonic_score = harmonic(
            match_count, len(reference), len(hypothesis), alpha, beta
        )

        lepor_scores.append(lp * npd * harmonic_score)

    return lepor_scores


def corpus_lepor(
    references: List[List[str]],
    hypothesis: List[str],
    alpha: float = 1.0,
    beta: float = 1.0,
    tokenizer: Callable[[str], List[str]] = None,
) -> List[List[float]]:
    """
    Calculate LEPOR score for list of sentences from Han, A. L.-F. (2017).
    LEPOR: An Augmented Machine Translation Evaluation Metric. https://arxiv.org/abs/1703.08748v2

    >>> hypothesis = ['a bird is on a stone.', 'scary crow was not bad.']

    >>> references = [['a bird behind the stone.', 'a bird is on the rock'],
    ...              ['scary cow was good.', 'scary crow was elegant.']]

    >>> corpus_lepor(references, hypothesis)
    [[0.7824248013113159, 0.7931427828105261], [0.5639427891892225, 0.7860963170056643]]


    :param references: Reference sentences
    :type references: list(list(str))
    :param hypothesis: Hypothesis sentences
    :type hypothesis: list(str)
    :param alpha: A parameter to set weight fot recall.
    :type alpha: float
    :param beta: A parameter to set weight fot precision.
    :type beta: float
    :param tokenizer: A callable tokenizer that will accept a string and returns a list of tokens.
    :type tokenizer: Callable[[str], List[str]]

    :return: The Lepor score. Returns a list for all sentences
    :rtype: list(list(float))

    """

    if len(references) == 0 or len(hypothesis) == 0:
        raise ValueError("There is an Empty list. Exit.")

    assert len(references) == len(hypothesis), (
        "The number of hypothesis and their reference(s) should be the " "same "
    )

    lepor_scores = list()

    for reference_sen, hypothesis_sen in zip(references, hypothesis):
        # Calculate Lepor for each sentence separately and append in a list.
        lepor_scores.append(
            sentence_lepor(reference_sen, hypothesis_sen, alpha, beta, tokenizer)
        )

    return lepor_scores
