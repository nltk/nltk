# Natural Language Toolkit: Language Model Counters
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals
from collections import defaultdict
from copy import copy

from nltk.probability import FreqDist, ConditionalFreqDist
from nltk import compat

from nltk.model.util import check_ngram_order, default_ngrams


def count_ngrams(order, vocabulary, *training_texts):
    counter = NgramCounter(order, vocabulary)
    ngram_gen = default_ngrams(order)
    for text in training_texts:
        counter.train_counts(map(ngram_gen, text))
    return counter


@compat.python_2_unicode_compatible
class NgramCounter(object):
    """Class for counting ngrams"""

    def __init__(self, order, vocabulary):
        """
        :type training_text: List[List[str]]
        """
        self.order = check_ngram_order(order)

        # Set up the vocabulary
        self.vocabulary = copy(vocabulary)  # copy needed to prevent state sharing

        self._ngram_orders = defaultdict(ConditionalFreqDist)
        self.unigrams = FreqDist()

    def train_counts(self, training_text):
        # Note here "1" indicates an empty vocabulary!
        # See NgramModelVocabulary __len__ method for more.
        if len(self.vocabulary) <= 1:
            raise ValueError("Cannot start counting ngrams until "
                             "vocabulary contains more than one item.")

        for sent in training_text:
            for ngram in sent:
                if not isinstance(ngram, tuple):
                    raise TypeError("Ngram <{0}> isn't a tuple, "
                                    "but {1}".format(ngram, type(ngram)))

                ngram_order = len(ngram)

                if ngram_order > self.order:
                    raise ValueError("Ngram larger than highest order: " "{0}".format(ngram))
                if ngram_order == 1:
                    self.unigrams[ngram[0]] += 1
                    continue

                context, word = ngram[:-1], ngram[-1]
                self[ngram_order][context][word] += 1

    def __getitem__(self, order_number):
        """For convenience allow looking up ngram orders directly here."""
        order_number = check_ngram_order(order_number, max_order=self.order)
        if order_number == 1:
            return self.unigrams
        return self._ngram_orders[order_number]
