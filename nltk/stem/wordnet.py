# Natural Language Toolkit: WordNet stemmer interface
#
# Copyright (C) 2001-2023 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import wordnet as wn


class WordNetLemmatizer:
    """
    WordNet Lemmatizer

    Provides 3 lemmatizer modes:

    1. _morphy() is an alias to WordNet's _morphy lemmatizer.
    It returns a list of all lemmas found in WordNet.

    >>> wnl = WordNetLemmatizer()
    >>> print(wnl._morphy('us', 'n'))
    ['us', 'u']

    2. morphy() is a restrictive wrapper around _morphy().
    It returns the first lemma found in WordNet,
    or None if no lemma is found.

    >>> print(wnl.morphy('us', 'n'))
    us

    >>> print(wnl.morphy('catss'))
    None

    3. lemmatize() is a permissive wrapper around _morphy().
    It returns the shortest lemma found in WordNet,
    or the input string unchanged if nothing is found.

    >>> print(wnl.lemmatize('us', 'n'))
    u

    >>> print(wnl.lemmatize('Anythinggoeszxcv'))
    Anythinggoeszxcv

    """

    morphy = wn.morphy

    _morphy = wn._morphy

    def lemmatize(self, word: str, pos: str = "n") -> str:
        """Lemmatize `word` by picking the shortest of the possible lemmas,
        using the wordnet corpus reader's built-in _morphy function.
        Returns the input word unchanged if it cannot be found in WordNet.

        >>> from nltk.stem import WordNetLemmatizer
        >>> wnl = WordNetLemmatizer()
        >>> print(wnl.lemmatize('dogs'))
        dog
        >>> print(wnl.lemmatize('churches'))
        church
        >>> print(wnl.lemmatize('aardwolves'))
        aardwolf
        >>> print(wnl.lemmatize('abaci'))
        abacus
        >>> print(wnl.lemmatize('hardrock'))
        hardrock

        :param word: The input word to lemmatize.
        :type word: str
        :param pos: The Part Of Speech tag. Valid options are `"n"` for nouns,
            `"v"` for verbs, `"a"` for adjectives, `"r"` for adverbs and `"s"`
            for satellite adjectives.
        :type pos: str
        :return: The shortest lemma of `word`, for the given `pos`.
        """
        lemmas = self._morphy(word, pos)
        return min(lemmas, key=len) if lemmas else word

    def __repr__(self):
        return "<WordNetLemmatizer>"
