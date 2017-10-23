# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from functools import partial
from math import log

from nltk.util import ngrams, everygrams, pad_sequence

NEG_INF = float("-inf")
POS_INF = float("inf")

NGRAMS_KWARGS = {
    "pad_left": True,
    "pad_right": True,
    "left_pad_symbol": "<s>",
    "right_pad_symbol": "</s>"
}


def log_base2(score):
    """Convenience function for computing logarithms with base 2"""
    if score == 0.0:
        return NEG_INF
    return log(score, 2)


def padded_everygrams(order,
                      sequence,
                      pad_left=True,
                      pad_right=True,
                      right_pad_symbol="</s>",
                      left_pad_symbol="<s>"):
    """Pads sequence *before* generating everygrams, not during."""
    padded = list(
        pad_sequence(
            sequence,
            order,
            pad_left=True,
            pad_right=True,
            right_pad_symbol="</s>",
            left_pad_symbol="<s>"))
    return everygrams(padded, max_len=order)


def default_ngrams(order):
    """Provides defaults for nltk.util.ngrams"""

    return partial(padded_everygrams, order)


def mask_oov_words_in_corpus(corpus, ngram_vocab):
    """Replace all out-of-vocabulary words in a corpus label for unknowns."""
    return [ngram_vocab.lookup(sent) for sent in corpus]
