# Natural Language Toolkit: Language Model Counters
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals
from collections import Counter, defaultdict
from copy import copy
from itertools import chain

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
class NgramModelVocabulary(Counter):
    """Stores language model vocabulary.

    Satisfies two common language modeling requirements for a vocabulary:
    - When checking membership and calculating its size, filters items by comparing
      their counts to a cutoff value.
    - Adds a special "unknown" token which unseen words are mapped to.

    >>> from nltk.corpus import gutenberg
    >>> sents = gutenberg.sents("burgess-busterbrown.txt")
    >>> test_words = [w for s in sents[3:5] for w in s]
    >>> test_words[:5]
    ['Buster', 'Bear', 'yawned', 'as', 'he']

    >>> from nltk.model import NgramModelVocabulary
    >>> vocab = NgramModelVocabulary(test_words, unk_cutoff=2)

    Tokens with counts greater than or equal to the cuttoff value will
    be considered part of the vocabulary.

    >>> vocab['the']
    3
    >>> 'the' in vocab
    True
    >>> vocab['he']
    2
    >>> 'he' in vocab
    True

    Tokens with frequency counts less than the cutoff value will be considered not
    part of the vocabulary even though their entries in the count dictionary are
    preserved.

    >>> vocab['Buster']
    1
    >>> 'Buster' in vocab
    False
    >>> vocab['aliens']
    0
    >>> 'aliens' in vocab
    False

    Keeping the count entries for seen words allows us to change the cutoff value
    without having to recalculate the counts.

    >>> vocab.cutoff = 1
    >>> "Buster" in vocab
    True

    The cutoff value influences not only membership checking but also the result of
    getting the size of the vocabulary using the built-in `len`.
    Note that while the number of keys in the vocab dictionary stays the same,
    the result of calling `len` on the vocabulary differs depending on the cutoff.

    >>> len(vocab.keys())
    38
    >>> len(vocab)
    38
    >>> vocab.cutoff = 2
    >>> len(vocab.keys())
    38
    >>> len(vocab)
    8

    """

    def __init__(self, *counter_args, unk_label="<UNK>", unk_cutoff=1):
        super(self.__class__, self).__init__(*counter_args)
        self.unk_label = unk_label
        self.cutoff = unk_cutoff

    @property
    def cutoff(self):
        """ Cutoff value.

        Items with count below this value are not considered part of the vocabulary.
        """
        return self._cutoff

    @cutoff.setter
    def cutoff(self, new_cutoff):
        if new_cutoff < 1:
            raise ValueError("Cutoff value cannot be less than 1. Got: {0}".format(new_cutoff))
        self._cutoff = new_cutoff
        self[self.unk_label] = new_cutoff

    def lookup_one(self, word):
        """Looks up one word in the vocabulary.

        :param str word: The word to look up.
        :return: `word` or `self.unk_label` if `word` isn't in vocabulary.
        :rtype: str
        """
        return word if word in self else self.unk_label

    def lookup(self, words):
        """Look up a sequence of words in the vocabulary.

        Returns an iterator over looked up words.

        :param Iterable(str) words: Sequence of words to look up.
        :rtype: Iterable(str)
        """
        return map(self.lookup_one, words)

    def __contains__(self, item):
        """Only consider items with counts GE to cutoff as being in the vocabulary."""
        return self[item] >= self.cutoff

    def __iter__(self):
        """Building on membership check define how to iterate over vocabulary."""
        return (item for item in super(NgramModelVocabulary, self).__iter__() if item in self)

    def __len__(self):
        """Computing size of vocabulary reflects the cutoff."""
        return sum(1 for item in self)

    def __eq__(self, other):
        return (super(self.__class__, self).__eq__(other) and (self.cutoff == other.cutoff))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.__class__(self, unk_cutoff=self.cutoff, unk_label=self.unk_label)


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
