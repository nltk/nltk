# Natural Language Toolkit: Splitta sentence tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Algorithm: Gillick (2009)
# Author: Dan Gillick <dgillick@gmail.com> (original Python implementation)
#         Sam Raker <sam.raker@gmail.com> (NLTK-compatible version)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
PairIter classes
"""

import re

from splitta.token_pair import TokenPair


# pylint: disable=no-member
class PairIterBase(object):
    """
    Base class for `PairIter`s.

    `PairIter`s are instantiated with a tokenizer, which is any class that
    inherits from :py:class:`nltk.tokenize.api.TokenizerI`
    or at least implements a method called `tokenize` that returns a
    sequence of strings.

    Each `PairIter` child class has an attribute `preprocessors`, which
    is a list of (`pat`, `replacement`) tuples, where `pat` is a (raw) string
    regular expression, and `replacement` is a replacement string.

    :py:class:`PairIterBase` isn't meant to be directly instantiated, but rather
    inherited from.
    """

    default_preprocessors = [(r'[.,\d]*\d', '<NUM>'), (r'--', ' ')]

    def __init__(self, tokenizer):
        """
        :param tokenizer: tokenizer to use when tokenizing text
        :type tokenizer: a class that inherits from
                         :py:class:`nltk.tokenize.api.TokenizerI` or
                         implements a `tokenize` method
        """
        self.tokenizer = tokenizer

    @classmethod
    def preprocess_token(cls, token):
        """
        Preprocess a token by replacing each instance of the pattern
        with the corresponding replacement string, in order. If the result
        is not a lone period or  empty string, it is returned, otherwise None
        is returned.

        :param str token: the token to process
        :return: preprocessed token or None
        :rtype str, None
        """

        for pat, replacement in cls.preprocessors:
            token = re.sub(pat, replacement, token)
        if token.replace('.', ''):
            return token
        return None

    def get_tokens(self, text):
        """
        Tokenize `text` using :py:meth:`.tokenizer.tokenize`, then yield
        non-`None` preprocessed tokens

        :param str text: the text to tokenize
        :return: preprocessed token
        :rtype: str
        """
        for token in self.tokenizer.tokenize(text):
            preprocessed = self.preprocess_token(token)
            if preprocessed is not None:
                yield preprocessed

    def pair_iter(self, text):
        """
        Yield labeled TokenPairs created from `text`

        :param str text: the text to iterate through
        :return: labeled :py:class:`token_pair.TokenPair`s
        :rtype: :py:class:`token_pair.TokenPair`
        """
        raise NotImplementedError


class RawPairIter(PairIterBase):
    """
    A `PairIter` that returns 'raw' (i.e. unprocessed)
    :py:class:`token_pair.TokenPair`s

    >>> s = "Hey there. You're cool."
    >>> tps = [TokenPair('Hey', 'there.', 'unlabeled'),
    ...     TokenPair('there.', 'You\'re', 'unlabeled'),
    ...     TokenPair('You\'re', 'cool.', 'unlabeled'),
    ...     TokenPair('cool.', None, 'non_boundary')]
    >>> pair_iter = RawPairIter(tokenize.regexp.WhiteSpaceTokenizer())
    >>> tps == list(pair_iter.pair_iter(s))
    """

    # no preprocessors--tokens returned 'as-is'
    preprocessors = []

    def __init__(self, tokenizer):
        """
        :param tokenizer: the tokenizer to use to tokenize text
        :type tokenizer: any class that inherits from
                         :py:class:`nltk.tokenize.api.TokenizeI`, or
                         implements a `tokenize` method
        """
        super(RawPairIter, self).__init__(tokenizer)

    def pair_iter(self, text):
        """
        Yield unprocessed TokenPair objects. Note that all TokenPairs
        are labeled 'unlabeled', except the final pair, which is always
        labeled 'non_candidate'.

        :param str text: the text to iterate through
        :return: labeled :py:class:`token_pair.TokenPair`s
        :rtype: :py:class:`token_pair.TokenPair`
        """
        tokens = self.get_tokens(text)
        prev = tokens.next()
        for token in tokens:
            yield TokenPair(prev, token, 'unlabeled')
            prev = token
        # final pair is always labeled as a non-candidate
        yield TokenPair(prev, None, 'non_candidate')


class TrainingPairIter(PairIterBase):
    """
    A `PairIter` that returns tokens from a training text. Training texts should
    be annotated.

    By default, labels are determined positively for boundaries and negatively
    for non-boundaries: a sequence `token1 <SB> token2` is labeled `boundary`,
    while a sequence `token1. token2` is labeled `non_boundary`, since it
    could be a boundary (the first token ends with a period), but isn't
    explicitly annotated.

    Explicit non-boundary annotations can be supplied, as can custom boundary
    annotations. More complex annotation-label mapping can be achieved by
    overriding :py:meth:`.get_next_token` in a subclass.

    >>> s = "Hey there. <SB> You're cool."
    >>> tps = [TokenPair('Hey', 'there.', 'non_candidate'),
    ...     TokenPair('there.', 'You\'re', 'boundary'),
    ...     TokenPair('You\'re', 'cool.', 'non_candidate'),
    ...     TokenPair('cool.', None, 'non_candidate')]
    >>> pair_iter = TrainingPairIter(
    ...     tokenize.regexp.WhiteSpaceTokenizer())
    >>> tps = list(pair_iter.pair_iter(s))
    """

    # default preprocessors, plus strip out all angle brackets that aren't
    # part of annotations
    preprocessors = PairIterBase.default_preprocessors + \
            [(r'(<(?!SB)|(?<!SB)>)', '')]

    def __init__(self, tokenizer, boundary_annotation='<SB>',
                 non_boundary_annotation=None):
        """
        Initialize a new :py:class:`TrainingPairIter`.
        :param tokenizer: object used to tokenize text
        :type tokenizer: any class that inherits from
                         :py:class:`nltk.tokenize.api.TokenizerI`, or at least
                         implements a tokenize method
        :param str boundary_annotation: the token marking a sentence boundary
        :param non_boundary_annotation: the token marking a lack of sentence
                                        boundary. If None, all potential
                                        boundaries (i.e., tokens ending with
                                        periods followed by whitespace and
                                        another token) will be labeled
                                        'non_boundary'.
        :type non_boundary_annotation: str, None
        """
        super(TrainingPairIter, self).__init__(tokenizer)
        self.annotations = {boundary_annotation: 'boundary'}
        if non_boundary_annotation:
            self.annotations[non_boundary_annotation] = 'non_boundary'

    def is_annotation(self, token):
        """
        Checks if `token` is an annotation.

        :param str token: the token to check
        :rtype: bool
        """
        return token in self.annotations.keys()

    def pair_iter(self, text):
        """
        Tokenize text and yield labeled :py:class:`token_pair.TokenPair`s from
        those tokens.

        :param str text: the text to tokenize
        :return: labeled :py:class:`token_pair.TokenPair`s
        :rtype: :py:class:`token_pair.TokenPair`
        """
        tokens = self.get_tokens(text)
        prev = tokens.next()
        while self.is_annotation(prev):
            prev = tokens.next()
        while True:
            token, label = self.get_next_token(tokens)
            yield TokenPair(prev, token, label)
            if token is None:
                break
            else:
                prev = token

    def get_next_token(self, tokens):
        """
        Advance the iterator through annotations until a non-annotation is
        encountered. Return that token and the label corresponding to the last
        annotation encountered

        :param tokens: the token iterator produced by :py:meth:`.get_tokens`
        :type tokens: generator
        :return: (token, label) tuples
        :rtype: str or None, str
        """
        label = 'non_candidate'
        while True:
            try:
                token = tokens.next()
                if self.is_annotation(token):
                    label = self.annotations[token]
                else:
                    return token, label
            except StopIteration:
                return None, 'non_candidate'


class TokenizingPairIter(PairIterBase):
    """
    A `PairIter` that returns :py:class:`token_pair.`TokenPair`s suitable for
    sentence-level tokenization using a trained classifier.
    :py:class:`TokenPair`s whose first token ends in a period are labeled
    `unlabeled`; other TokenPairs are labeled `non_candidate`.

    >>> s = "Hey there. You're cool."
    >>> tps = [TokenPair('Hey', 'there.', 'non_candidate'),
    ...     TokenPair('there.', 'You\'re', 'unlabeled'),
    ...     TokenPair('You\'re', 'cool.', 'non_candidate'),
    ...     TokenPair('cool.', None, 'non_candidate')]
    >>> pair_iter = TokenizingPairIter(tokenize.regexp.WhiteSpaceTokenizer())
    >>> tps == list(pair_iter.pair_iter(s)) # True
    """

    # default preprocessors plus stripping out all angle brackets
    preprocessors = PairIterBase.default_preprocessors + [(r'[<>]', '')]

    def __init__(self, tokenizer):
        """
        :param tokenizer: object used to tokenize text
        :type tokenizer: any class that inherits from
                         :py:class:`nltk.tokenize.api.TokenizerI`, or at least
                         implements a tokenize method
        """
        super(TokenizingPairIter, self).__init__(tokenizer)

    def pair_iter(self, text):
        """
        Tokenize text and return labeled TokenPairs from the tokens

        :param str text: the text to tokenize
        :return: labeled :py:class:`token_pair.TokenPair`s
        :rtype: :py:class:`token_pair.TokenPair`
        """
        tokens = self.get_tokens(text)
        prev = tokens.next()
        for token in tokens:
            if prev.endswith('.'):
                yield TokenPair(prev, token, 'unlabeled')
            else:
                yield TokenPair(prev, token, 'non_candidate')
            prev = token
        yield TokenPair(prev, None, 'non_candidate')

