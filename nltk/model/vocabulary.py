# Natural Language Toolkit: Language Model Vocabulary
#
# Copyright (C) 2001-2017 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
Building a Vocabulary
---------------------

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

    We can look up words in a vocabulary using its `lookup` method.
    "Unseen" words (with counts less than cutoff) are looked up as the unknown label.
    If given one word (a string) as an input, this method will return a string.

    >>> vocab.lookup("he")
    'he'
    >>> vocab.lookup("aliens")
    '<UNK>'

    If given a sequence (anything other than a string), it will return an iterator over
    the looked up words.

    >>> list(vocab.lookup(sents[5][:5]))
    ['<UNK>', 'he', '<UNK>', '<UNK>', 'to']

"""

from __future__ import unicode_literals
from functools import singledispatch
from collections import Counter

from nltk import compat


@singledispatch
def _dispatched_lookup(words, vocab):
    """Look up a sequence of words in the vocabulary.

    Returns an iterator over looked up words.
    """
    return (w if w in vocab else vocab.unk_label for w in words)


@_dispatched_lookup.register(str)
def _(word, vocab):
    """Looks up one word in the vocabulary."""
    return word if word in vocab else vocab.unk_label


@compat.python_2_unicode_compatible
class NgramModelVocabulary(Counter):
    """Stores language model vocabulary.

    Satisfies two common language modeling requirements for a vocabulary:
    - When checking membership and calculating its size, filters items
      by comparing their counts to a cutoff value.
    - Adds a special "unknown" token which unseen words are mapped to.

    >>> from nltk.model import NgramModelVocabulary
    >>> vocab = NgramModelVocabulary(["a", "b", "c", "a", "b"], unk_cutoff=2)
    >>> "a" in vocab
    True
    >>> "c" in vocab
    False
    >>> len(vocab)
    3
    >>> len(vocab.keys())
    4
    """

    def __init__(self, *counter_args, unk_cutoff=1, unk_label="<UNK>"):
        """Create a new NgramModelVocabulary.

        :param *counter_args: Same arguments as for `collections.Counter`.
        :param int unk_cutoff: Words that occur less frequently than this value
                               are not considered part of the vocabulary.
        :param unk_label: Label for marking words not considered part of the vocabulary.
        """
        super(NgramModelVocabulary, self).__init__(*counter_args)
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

    def lookup(self, words):
        """Look up one or more words in the vocabulary.

        If passed one word as a string will return that word or `self.unk_label`.
        Otherwise will assume it was passed a sequence of words, will try to look
        each of them up and return an iterator over the looked up words.

        :param words: Word(s) to look up.
        :type words: Iterable(str) or str
        :rtype: generator(str) or str

        >>> from nltk.model import NgramModelVocabulary
        >>> vocab = NgramModelVocabulary(["a", "b", "c", "a", "b"], unk_cutoff=2)
        >>> vocab.lookup("a")
        'a'
        >>> vocab.lookup("aliens")
        '<UNK>'
        >>> list(vocab.lookup(["a", "b", "c"]))
        ['a', 'b', '<UNK>']
        """
        return _dispatched_lookup(words, self)

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
        return super(NgramModelVocabulary, self).__eq__(other) and (self.cutoff == other.cutoff)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.__class__(self, unk_cutoff=self.cutoff, unk_label=self.unk_label)
