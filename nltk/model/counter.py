# Natural Language Toolkit: Language Model Counters
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

from collections import Counter, defaultdict
from itertools import chain

from nltk.util import ngrams
from nltk.probability import FreqDist, ConditionalFreqDist
from nltk import compat


@compat.python_2_unicode_compatible
class NgramModelVocabulary(Counter):
    """Stores language model vocabulary.

    Satisfies two common language modeling requirements for a vocabulary:
    - When checking membership and calculating its size, filters items by comparing
      their counts to a cutoff value.
    - Adds 1 to its size so as to account for "unknown" tokens.
    """

    def __init__(self, unknown_cutoff, *counter_args):
        Counter.__init__(self, *counter_args)
        self.cutoff = unknown_cutoff

    @property
    def cutoff(self):
        return self._cutoff

    @cutoff.setter
    def cutoff(self, new_cutoff):
        if new_cutoff < 1:
            msg_template = "Cutoff value cannot be less than 1. Got: {0}"
            raise ValueError(msg_template.format(new_cutoff))
        self._cutoff = new_cutoff

    def __contains__(self, item):
        """Only consider items with counts GE to cutoff as being in the vocabulary."""
        return self[item] >= self.cutoff

    def __len__(self):
        """This should reflect a) filtering items by count, b) accounting for unknowns.

        The first is achieved by relying on the membership check implementation.
        The second is achieved by adding 1 to vocabulary size.
        """
        # the if-clause here looks a bit dumb, should we make it clearer?
        return sum(1 for item in self if item in self) + 1


@compat.python_2_unicode_compatible
class EmptyVocabularyError(Exception):
    pass


@compat.python_2_unicode_compatible
class NgramCounter(object):
    """Class for counting ngrams"""

    def __init__(self, highest_order, vocabulary, unk_cutoff=None,
                 unk_label="<UNK>", start_symbol="<s>", end_symbol="</s>"):
        """
        :type training_text: List[List[str]]
        """

        if highest_order < 1:
            message = "Order of NgramCounter cannot be less than 1. Got: {0}"
            raise ValueError(message.format(highest_order))

        self.order = highest_order
        self.start_symbol = start_symbol
        self.end_symbol = end_symbol
        self.unk_label = unk_label

        self.vocabulary = vocabulary
        if unk_cutoff is not None:
            # If cutoff value is provided, override vocab's cutoff
            self.vocabulary.cutoff = unk_cutoff
        self.ngrams = defaultdict(ConditionalFreqDist)
        self.unigrams = FreqDist()

    def _enumerate_ngram_orders(self):
        return enumerate(range(self.order, 1, -1))

    def count_ngrams(self, training_text):
        # Note here "1" indicates an empty vocabulary!
        # See NgramModelVocabulary __len__ method for more.
        if len(self.vocabulary) <= 1:
            raise EmptyVocabularyError("Cannot start counting ngrams until "
                                       "vocabulary contains more than one item.")

        for sent in training_text:
            checked_sent = (self.check_against_vocab(word) for word in sent)
            for ngram in self.padded_ngrams(checked_sent):
                context, word = tuple(ngram[:-1]), ngram[-1]
                for trunc_index, ngram_order in self._enumerate_ngram_orders():
                    trunc_context = context[trunc_index:]
                    # note that above line doesn't affect context on first iteration
                    self.ngrams[ngram_order][trunc_context][word] += 1
                self.unigrams[word] += 1

    def check_against_vocab(self, word):
        if word in self.vocabulary:
            return word
        return self.unk_label

    def padded_ngrams(self, sequence):
        """Wrapper around util.ngrams with usefull options saved during initialization.

        :param sequence: same as nltk.util.ngrams
        :type sequence: any iterable
        """
        return ngrams(sequence, self.order, pad_left=True, pad_right=True,
                      left_pad_symbol=self.start_symbol,
                      right_pad_symbol=self.end_symbol)
