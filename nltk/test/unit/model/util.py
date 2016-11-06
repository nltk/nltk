# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT


def mask_oov_words_in_corpus(corpus, ngram_vocab):
    """Replace all out-of-vocabulary words in a corpus label for unknowns."""
    return [list(map(ngram_vocab.mask_oov, sent)) for sent in corpus]


def default_ngrams(order):
    """Provides defaults for nltk.util.ngrams"""
    ngrams_kwargs = {
        "pad_left": True,
        "pad_right": True,
        "left_pad_symbol": "<s>",
        "right_pad_symbol": "</s>"
    }

    def to_ngrams(sequence):
        """Wrapper around util.ngrams with usefull options saved during initialization.

        :param sequence: same as nltk.util.ngrams
        :type sequence: any iterable
        """
        return ngrams(sequence, order, **ngrams_kwargs)

    return to_ngrams


class NgramCounterSetUpMixin(object):
    """To be used with unittest.TestCase classes.

    Requires them to have self.vocab already defined.
    """
    def setUpNgramCounter(order, corpus, attr_name="counter")

