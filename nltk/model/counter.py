# Natural Language Toolkit: Language Model Counters
#
# Copyright (C) 2001-2017 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
Counting Ngrams
---------------

First we need to make sure we are feeding the counter ngrams.

    >>> text = [list("abcd"), list("acdc")]
    >>> from nltk.util import everygrams
    >>> text_ngrams = (everygrams(sent, max_len=2) for sent in text)

The counting itself is very simple.

    >>> from nltk.model import NgramCounter
    >>> ngram_counts = NgramCounter(text_ngrams)

The counts are stored by ngram order. I.e. here's how you access bigrams.

    >>> ngram_counts[2]
    <ConditionalFreqDist with 4 conditions>

The keys of this `ConditionalFreqDist` are the contexts preceding a word.
Each context has a `FreqDist` of tokens found following it in the text.

    >>> ngram_counts[2][('a',)]
    FreqDist({'b': 1, 'c': 1})

Accessing unigram counts works a little differently because they don't have any
preceding context. They are stored as a simple `FreqDist` in the `unigrams`
attribute.

    >>> print(ngram_counts.unigrams)
    <FreqDist with 4 samples and 8 outcomes>
    >>> ngram_counts.unigrams['a']
    2
    >>> ngram_counts.unigrams['c']
    3

You can also access them using square bracket notation.

    >>> ngram_counts[1]['b']
    1
"""

from __future__ import unicode_literals
from collections import defaultdict

from nltk.probability import FreqDist, ConditionalFreqDist
from nltk import compat

from nltk.model.util import default_ngrams


def check_ngram_order(order_to_check, max_order=1000):
    """Sanity-check ngram order number."""
    if order_to_check < 1:
        raise ValueError("Ngram order cannot be less than 1. Got: {0}".format(order_to_check))
    if order_to_check > max_order:
        raise ValueError("Ngram order cannot be greater than {0}. Got: {1}".format(
            max_order, order_to_check))
    return order_to_check


@compat.python_2_unicode_compatible
class NgramCounter(defaultdict):
    """Class for counting ngrams.

    Will count any ngram sequence you give it.

    >>> from nltk.model import NgramCounter
    >>> counts = NgramCounter([[('a', 'b'), ('b', 'c')], [('d', 'e'), ('e', 'f')]])
    >>> counts[2]
    <ConditionalFreqDist with 4 conditions>
    >>> counts[2][('a',)]['b']
    1
    >>> counts.unigrams
    FreqDist({})
    >>> counts.update([[('a',), ('b',), ('b',)]])
    >>> counts.unigrams
    FreqDist({'b': 2, 'a': 1})
    >>> counts.unigrams['b']
    2

    """

    def __init__(self, ngram_text=None):
        """Creates a new NgramCounter.

        If `ngram_text` is specified, counts ngrams from it, otherwise waits for
        `update` method to be called explicitly.

        :param ngram_text: Optional text containing senteces of ngrams, as for `update` method.
        :type ngram_text: Iterable(Iterable(tuple(str))) or None

        """
        super(NgramCounter, self).__init__(ConditionalFreqDist)
        self[1] = FreqDist()
        self.unigrams = self[1]

        if ngram_text:
            self.update(ngram_text)

    def update(self, ngram_text):
        """Updates ngram counts from `ngram_text`.

        Expects `ngram_text` to be a sequence of sentences (sequences).
        Each sentence consists of ngrams as tuples of strings.

        :param Iterable(Iterable(tuple(str))) ngram_text: Text containing senteces of ngrams.
        :raises TypeError: if the ngrams are not tuples.

        """

        for sent in ngram_text:
            for ngram in sent:
                if not isinstance(ngram, tuple):
                    raise TypeError("Ngram <{0}> isn't a tuple, but {1}".format(ngram, type(ngram)))

                ngram_order = len(ngram)
                if ngram_order == 1:
                    self.unigrams[ngram[0]] += 1
                    continue

                context, word = ngram[:-1], ngram[-1]
                self[ngram_order][context][word] += 1

    def N(self):
        """Returns grand total number of ngrams stored.

        This includes ngrams from all orders, so some duplication is expected.
        :rtype: int

        >>> from nltk.model import NgramCounter
        >>> counts = NgramCounter([[("a", "b"), ("c",), ("d", "e")]])
        >>> counts.N()
        3

        """
        return sum(self[order].N() for order in self)

    def freq_of_freq(self):
        """Maps frequencies of ngrams to how many ngrams occurred with each
        frequency.

        Equivalent to `FreqDist.r_Nr`, but more explicitly named.
        Returns a dictionary where the keys are the ngram orders of NgramCounter instance.
        The values are defaultdicts of ints to ints.
        In the defaultdicts each key is an ngram frequency and its corresponding value
        is how many ngrams occurred with that frequency.

        :rtype: dict(defaultdict(int))

        >>> from nltk.model import NgramCounter
        >>> counts = NgramCounter([[("a", "c"), ("d", "c"), ("c",)]])
        >>> r_Nr = counts.freq_of_freq()
        >>> r_Nr[1]
        defaultdict(<class 'int'>, {1: 1, 0: 0})
        >>> r_Nr[2]
        defaultdict(<class 'int'>, {1: 2})

        """
        _r_Nr = {}
        for order in self:
            if order == 1:
                _r_Nr[order] = self[order].r_Nr()
                continue

            _r_Nr[order] = defaultdict(int)
            for fdist in self[order].values():
                for freq in fdist.values():
                    _r_Nr[order][freq] += 1
        return _r_Nr

    def __str__(self):
        return "<{0} with {1} ngram orders and {2} ngrams>".format(self.__class__.__name__,
                                                                   len(self), self.N())
