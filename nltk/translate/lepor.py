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

import nltk


def length_penalty(reference: list[str], hypothesis: list[str]) -> float:
    """
    Function will calculate length penalty(LP) one of the components in LEPOR, which is defined to embrace
    the penalty for both longer and shorter hypothesis compared with the reference translations.

    :param reference: reference sentence
    :type reference: str
    :param hypothesis: hypothesis sentence
    :type hypothesis: str

    :return: penalty of difference in length in reference and hypothesis sentence.
    :rtype: float
    """

    r_len = len(reference)
    o_len = len(hypothesis)

    if r_len == o_len:
        return 1
    elif r_len < o_len:
        return math.exp(1 - (r_len / o_len))
    else:
        return math.exp(1 - (o_len / r_len))


def ngram_positional_penalty(ref_words: list[str], hypothesis_words: list[str]) -> (float, float):
    """
    Function will calculate penalty due to difference in positions of ngram in reference and output sentences.

    :param ref_words: list of words in reference sentence.
    :type ref_words: list[str]
    :param hypothesis_words: list of words in hypothesis sentence.
    :type hypothesis_words: list[str]

    :return: A tuple containing two elements:
             - NPosPenal: N-gram positional penalty.
             - match_count: Count of matched n-grams.
    :rtype: tuple
    """

    alignments = []

    for hyp_index, hyp_word in enumerate(hypothesis_words):

        if ref_words.count(hyp_word) == 0:
            # No match
            alignments.append(-1)
        elif ref_words.count(hyp_word) == 1:
            # If only one match
            alignments.append(ref_words.index(hyp_word))
        else:
            # if there are multiple possibilities.
            ref_indexes = [i for i, word in enumerate(ref_words) if word == hyp_word]

            is_matched = [False] * len(ref_indexes)

            for ind, ref_word_index in enumerate(ref_indexes):
                if 0 < ref_word_index - 1 < len(ref_words) and 0 < hyp_index - 1 < len(hypothesis_words) \
                        and ref_words[ref_word_index - 1] == hypothesis_words[hyp_index - 1]:
                    is_matched[ind] = True
                elif 0 < ref_word_index + 1 < len(ref_words) and 0 < hyp_index + 1 < len(hypothesis_words) \
                        and ref_words[ref_word_index + 1] == hypothesis_words[hyp_index + 1]:
                    is_matched[ind] = True

            if is_matched.count(True) == 1:
                alignments.append(ref_indexes[is_matched.index(True)])
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

            else:
                min_distance = 0
                min_index = 0
                for ref_index in ref_indexes:
                    distance = abs(hyp_index - ref_index)
                    if distance > min_distance:
                        min_distance = distance
                        min_index = ref_index
                alignments.append(min_index)

    alignments = [a + 1 for a in alignments if a != -1]
    match_count = len(alignments)
    npd_list = []

    for ind, a in enumerate(alignments):
        npd_list.append(abs(((ind + 1) / len(hypothesis_words)) - (a / len(ref_words))))
    npd = sum(npd_list) / len(hypothesis_words)

    return math.exp(-npd), match_count


def harmonic(match_count: int,
             reference_length: int,
             hypothesis_length: int,
             alpha: float,
             beta: float) -> float:
    """
    Function will calculate the precision and recall of matched words and calculate a final score on wighting
    using alpha and beta parameters.

    :param match_count: number of words in hypothesis aligned with reference.
    :type match_count: int
    :param reference_length: length of the reference sentence
    :type reference_length: int
    :param hypothesis_length: length of the hypothesis sentence
    :type hypothesis_length: int
    :param alpha: a parameter to set weight fot recall.
    :type alpha: float
    :param beta: a parameter to set weight fot precision.
    :type beta: float

    :return: harmonic mean.
    :rtype: float
    """

    epsilon = sys.float_info.epsilon

    precision = match_count / hypothesis_length
    recall = match_count / reference_length

    harmonic_score = (alpha + beta) / ((alpha / (recall + epsilon)) + (beta / (precision + epsilon)))

    return harmonic_score


def sentence_lepor(reference: str,
                   hypothesis: str,
                   alpha: float = 1.0,
                   beta: float = 1.0) -> float:
    """
    Calculate LEPOR score a sentence from Han, A. L.-F. (2017).
    LEPOR: An Augmented Machine Translation Evaluation Metric. https://arxiv.org/abs/1703.08748v2

    >>> hypothesis = 'a bird is on a stone.'

    >>> references = 'a bird behind the stone.'

    >>> sentence_lepor(references, hypothesis)
    0.7824248013113159

    :param reference: reference sentence
    :type reference: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param alpha: a parameter to set weight fot recall.
    :type alpha: float
    :param beta: a parameter to set weight fot precision.
    :type beta: float

    :return: The Lepor score. Returns a float value of lepor score for a sentence
    :rtype: float

    """

    if len(reference) == 0 or len(hypothesis) == 0:
        raise ValueError("One of the sentence is empty. Exit.")

    # Regex to remove all the unnecessary punctuation from the text.
    reference = nltk.word_tokenize(reference)
    hypothesis = nltk.word_tokenize(hypothesis)

    # reference = re.findall(r"[\w']+|[.,!?;]", reference)
    # hypothesis = re.findall(r"[\w']+|[.,!?;]", hypothesis)

    # Calculate the length penalty due to the difference in the length of reference and hypothesis.
    lp = length_penalty(reference, hypothesis)

    # Calculate the penalty on different positions of same word in translation.
    npd, match_count = ngram_positional_penalty(reference, hypothesis)

    harmonic_score = harmonic(match_count, len(reference), len(hypothesis), alpha, beta)

    return lp * npd * harmonic_score


def corpus_lepor(references: list[str],
                 hypothesis: list[str],
                 alpha: float = 1.0,
                 beta: float = 1.0) -> list[float]:
    """
    Calculate LEPOR score for list of sentences from Han, A. L.-F. (2017).
    LEPOR: An Augmented Machine Translation Evaluation Metric. https://arxiv.org/abs/1703.08748v2

    >>> hypothesis = ['a bird is on a stone.', 'scary crow was not bad.']

    >>> references = ['a bird behind the stone.', 'scary cow was good.']

    >>> corpus_lepor(references, hypothesis)
    [0.7824248013113159, 0.5639427891892225]


    :param references: reference sentences
    :type references: list(list(str))
    :param hypothesis: hypothesis sentences
    :type hypothesis: list(str)
    :param alpha: a parameter to set weight fot recall.
    :type alpha: float
    :param beta: a parameter to set weight fot precision.
    :type beta: float

    :return: The Lepor score. Returns a list for all sentences
    :rtype: list(float)

    """

    if len(reference) == 0 or len(hypothesis) == 0:
        raise ValueError("There is an Empty list. Exit.")

    assert len(references) == len(hypothesis), (
        "The number of hypothesis and their reference(s) should be the " "same "
    )

    lepor_scores = list()

    for reference_sen, hypothesis_sen in zip(references, hypothesis):
        # Calculate Lepor for each sentence separately and append in a list.
        lepor_scores.append(sentence_lepor(reference_sen, hypothesis_sen, alpha, beta))

    return lepor_scores
