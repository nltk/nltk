# Natural Language Toolkit: Splitta sentence tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Algorithm: Gillick (2009)
# Author: Dan Gillick <dgillick@gmail.com> (original Python implementation)
#         Sam Raker <sam.raker@gmail.com> (NLTK-compatible version)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
TokenPair class
"""
class TokenPair(object):
    """
    Stores a pair of tokens and the label associated with them. Note that
    what is labeled is actually the break between the tokens, e.g.

    >>> tp = TokenPair('end.', 'The', 'boundary')
    >>> tp.label == 'boundary'
    >>> tp.tokens == ('end.', 'The')
    # 'end.' ends a sentence, 'The' starts another one
    """

    # labels are stored as ints internally, but set and retrieved as strings
    label_list = ['non_candidate', 'unlabeled', 'boundary', 'non_boundary']
    label_dict = dict(zip(label_list, xrange(len(label_list))))

    __slots__ = ['tokens', '_label']

    def __init__(self, token1, token2, label):
        """
        Create a new :py:class:`TokenPair` with the given label

        :param str token1: the first token
        :param str token2: the second token
        :param str label: the :py:class:`TokenPair`'s label
        """
        self.tokens = (token1, token2)
        self._label = self.validate_label(label)

    def __str__(self):
        if self.tokens[1] is None:
            return self.tokens[0]
        else:
            return " ".join(self.tokens)

    @property
    def label(self):
        """
        The label associated with this :py:class:`TokenPair`
        """
        return self.label_list[self._label]

    def validate_label(self, label_name):
        """
        Ensure a :py:class`TokenPair` is assigned a valid label

        :param str label_name: the label to assign
        """
        label_name = label_name or 'unlabeled'
        return self.label_dict[label_name]

    @label.setter
    def label(self, label_name):
        """
        Validate and set :py:attr:`.label`

        :param str label_name: the label to assign
        """
        self._label = self.validate_label(label_name)

    @label.deleter
    def label(self):
        """
        Set :py:attr:`.label` to `unlabeled` instead of deleting it
        """
        self._label = self.label_dict['unlabeled']

