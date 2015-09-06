# Multi-Word Expression tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Rob Malouf <rmalouf@mail.sdsu.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Multi-Word Expression Tokenizer

A ``MWETokenizer`` takes a string which has already been divided into tokens and
retokenizes it, merging multi-word expressions into single tokens, using a lexicon
of MWEs:


    >>> from nltk.tokenize import MWETokenizer

    >>> tokenizer = MWETokenizer([('a', 'little'), ('a', 'little', 'bit'), ('a', 'lot')])
    >>> tokenizer.add_mwe(('in', 'spite', 'of'))

    >>> tokenizer.tokenize('Testing testing testing one two three'.split())
    ['Testing', 'testing', 'testing', 'one', 'two', 'three']

    >>> tokenizer.tokenize('This is a test in spite'.split())
    ['This', 'is', 'a', 'test', 'in', 'spite']

    >>> tokenizer.tokenize('In a little or a little bit or a lot in spite of'.split())
    ['In', 'a_little', 'or', 'a_little_bit', 'or', 'a_lot', 'in_spite_of']

"""

from nltk.tokenize.api import TokenizerI


class MWETokenizer(TokenizerI):
    """
    A tokenizer that processes tokenized text and merges multi-word expressions
    into single tokens:

        >>> tokenizer = MWETokenizer([('hors', "d'oeuvre")], separator='+')
        >>> tokenizer.tokenize("An hors d'oeuvre tonight, sir?".split())
        ['An', "hors+d'oeuvre", 'tonight,', 'sir?']

    :type mwes: list(list(str))
    :param mwes: A sequence of multi-word expressions to be merged, where
        each MWE is a sequence of strings.
    :type separator: str
    :param separator: String that should be inserted between words in a multi-word
        expression token.

    """

    def __init__(self, mwes=None, separator='_'):

        if not mwes:
            mwes = []
        self._mwes = dict()
        self._separator = separator
        for mwe in mwes:
            self.add_mwe(mwe)

    def add_mwe(self, mwe, _trie=None):
        """
        Add a multi-word expression to the lexicon (stored as a word trie)

        We represent the trie as a dict of dicts:

            >>> tokenizer = MWETokenizer([('a', 'b'), ('a', 'b', 'c'), ('a', 'x')])
            >>> tokenizer._mwes
            {'a': {'x': {True: None}, 'b': {True: None, 'c': {True: None}}}}

        The key True marks the end of a valid MWE

        """

        if _trie is None:
            _trie = self._mwes
        if mwe:
            if mwe[0] not in _trie:
                _trie[mwe[0]] = dict()
            self.add_mwe(mwe[1:], _trie=_trie[mwe[0]])
        else:
            _trie[True] = None

    def tokenize(self, text):

        i = 0
        n = len(text)
        result = []

        while i < n:
            if text[i] in self._mwes:
                # possible MWE match
                j = i
                trie = self._mwes
                while j < n and text[j] in trie:
                    trie = trie[text[j]]
                    j = j + 1
                else:
                    if True in trie:
                        # success!
                        result.append(self._separator.join(text[i:j]))
                        i = j
                    else:
                        # no match, so backtrack
                        result.append(text[i])
                        i += 1
            else:
                result.append(text[i])
                i += 1

        return result
