# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk.model import NgramCounter
from nltk.model.util import (default_ngrams,
                             mask_oov_words_in_corpus,
                             NGRAMS_KWARGS)


class NgramCounterSetUpMixin(object):
    """To be used with unittest.TestCase classes.

    Requires them to have cls.vocab already defined.
    """
    @classmethod
    def setUpNgramCounter(cls, order, corpus, vocab=None):
        vocab = vocab or cls.vocab
        vocab[NGRAMS_KWARGS['left_pad_symbol']] = vocab.cutoff
        vocab[NGRAMS_KWARGS['right_pad_symbol']] = vocab.cutoff
        normalized = mask_oov_words_in_corpus(corpus, vocab)
        counter = NgramCounter(order, vocab)
        counter.train_counts(map(default_ngrams(order), normalized))
        return counter
