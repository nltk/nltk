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


def length_penalty(reference: list[str], hypotheses: list[str]) -> float:
    """
    Function will calculate length penalty(LP) one of the components in LEPOR, which is defined to embrace
    the penalty for both longer and shorter hypothesis compared with the reference translations.

    Args:
        reference: reference sentence
        hypotheses: output sentence by a translation engine.
    Return:
        LP: penalty of difference in length in reference and output sentence.
    """

    r_len = len(reference)
    o_len = len(hypotheses)

    if r_len == o_len:
        return 1
    elif r_len < o_len:
        return math.exp(1 - (r_len / o_len))
    else:
        return math.exp(1 - (o_len / r_len))


def ngram_positional_penalty(ref_words: list[str], hypotheses_words: list[str]) -> (float, float):
    """
    Function will calculate penalty due to difference in positions of ngram in reference and output sentences.

    Args:
        ref_words: reference sentence
        hypotheses_words: output sentence by a translation engine.
    Return:
        NPosPenal: penalty due to difference in positions of ngram in reference and output sentences.
    """

    alignments = []

    for hyp_index, hyp_word in enumerate(hypotheses_words):

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
                if 0 < ref_word_index - 1 < len(ref_words) and 0 < hyp_index - 1 < len(hypotheses_words) \
                        and ref_words[ref_word_index - 1] == hypotheses_words[hyp_index - 1]:
                    is_matched[ind] = True
                elif 0 < ref_word_index + 1 < len(ref_words) and 0 < hyp_index + 1 < len(hypotheses_words) \
                        and ref_words[ref_word_index + 1] == hypotheses_words[hyp_index + 1]:
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
        npd_list.append(abs(((ind + 1) / len(hypotheses_words)) - (a / len(ref_words))))
    npd = sum(npd_list) / len(hypotheses_words)

    return math.exp(-npd), match_count


def harmonic(match_count: int,
             reference_length: int,
             hypotheses_length: int,
             alpha: float,
             beta: float) -> float:
    """
    Function will calculate the percison and recall of matced words and calculate a final score on wighting using alpha
    and beta parameters

    Args:
        match_count: number of words in output aligned with reference.
        reference_length:  length of reference sentence.
        hypotheses_length: length of output sentence
        alpha: weighting parameter
        beta: weighting parameter
    """

    epsilon = sys.float_info.epsilon

    precision = match_count / hypotheses_length
    recall = match_count / reference_length

    harmonic_score = (alpha + beta) / ((alpha / (recall + epsilon)) + (beta / (precision + epsilon)))

    return harmonic_score


def sentence_lepor(reference: str,
                   hypotheses: str,
                   alpha: float = 1.0,
                   beta: float = 1.0) -> float:
    """
    Calculates the LEPOR score for one sentence.

    Args:
        reference: reference sentence/ ground truth
        hypotheses: output of translation engine
        alpha: a parameter to set the weight for recall.
        beta: a parameter to set the weight for precision.
    Returns:
        lepor score for one sentence.
    """

    if len(reference) == 0 or len(hypotheses) == 0:
        raise ValueError("One of the sentence is empty. Exit.")

    # Regex to remove all the unnecessary punctuation from the text.
    reference = nltk.word_tokenize(reference)
    hypotheses = nltk.word_tokenize(hypotheses)

    # reference = re.findall(r"[\w']+|[.,!?;]", reference)
    # hypotheses = re.findall(r"[\w']+|[.,!?;]", hypotheses)

    # Calculate the length penalty due to the difference in the length of reference and hypotheses.
    lp = length_penalty(reference, hypotheses)

    # Calculate the penalty on different positions of same word in translation.
    npd, match_count = ngram_positional_penalty(reference, hypotheses)

    harmonic_score = harmonic(match_count, len(reference), len(hypotheses), alpha, beta)

    return lp * npd * harmonic_score


def corpus_lepor(references: list[str],
                 hypotheses: list[str],
                 alpha: float = 1.0,
                 beta: float = 1.0) -> list[float]:
    """
    Args:
        references: list of reference sentences.
        hypotheses: list of sentences given by the translation engine/model.
        alpha: a parameter to set the weight for recall.
        beta: a parameter to set the weight for precision.

    Returns:
        lepor_scores: list of lepor scores for all sentences.
    """

    if len(reference) == 0 or len(hypothesis) == 0:
        raise ValueError("There is an Empty list. Exit.")

    assert len(references) == len(hypotheses), (
        "The number of hypotheses and their reference(s) should be the " "same "
    )

    lepor_scores = list()

    for reference_sen, hypotheses_sen in zip(references, hypotheses):
        # Calculate Lepor for each sentence separately and append in a list.
        lepor_scores.append(sentence_lepor(reference_sen, hypotheses_sen, alpha, beta))

    return lepor_scores
