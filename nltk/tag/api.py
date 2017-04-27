# Natural Language Toolkit: Tagger Interface
#
# Copyright (C) 2001-2017 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Interface for tagging each token in a sentence with supplementary
information, such as its part of speech.
"""
from itertools import chain

from nltk.internals import overridden
from nltk.metrics import accuracy

from nltk.tag.util import untag

class TaggerI(object):
    """
    A processing interface for assigning a tag to each token in a list.
    Tags are case sensitive strings that identify some property of each
    token, such as its part of speech or its sense.

    Some taggers require specific types for their tokens.  This is
    generally indicated by the use of a sub-interface to ``TaggerI``.
    For example, featureset taggers, which are subclassed from
    ``FeaturesetTagger``, require that each token be a ``featureset``.

    Subclasses must define:
      - either ``tag()`` or ``tag_sents()`` (or both)
    """
    def tag(self, tokens):
        """
        Determine the most appropriate tag sequence for the given
        token sequence, and return a corresponding list of tagged
        tokens.  A tagged token is encoded as a tuple ``(token, tag)``.

        :rtype: list(tuple(str, str))
        """
        if overridden(self.tag_sents):
            return self.tag_sents([tokens])[0]
        else:
            raise NotImplementedError()

    def tag_sents(self, sentences):
        """
        Apply ``self.tag()`` to each element of *sentences*.  I.e.:

            return [self.tag(sent) for sent in sentences]
        """
        return [self.tag(sent) for sent in sentences]

    def evaluate(self, gold):
        """
        Score the accuracy of the tagger against the gold standard.
        Strip the tags from the gold standard text, retag it using
        the tagger, then compute the accuracy score.

        :type gold: list(list(tuple(str, str)))
        :param gold: The list of tagged sentences to score the tagger on.
        :rtype: float
        """

        tagged_sents = self.tag_sents(untag(sent) for sent in gold)
        gold_tokens = list(chain(*gold))
        test_tokens = list(chain(*tagged_sents))
        return accuracy(gold_tokens, test_tokens)

    def _check_params(self, train, model):
        if (train and model) or (not train and not model):
            raise ValueError('Must specify either training data or trained model.')

class FeaturesetTaggerI(TaggerI):
    """
    A tagger that requires tokens to be ``featuresets``.  A featureset
    is a dictionary that maps from feature names to feature
    values.  See ``nltk.classify`` for more information about features
    and featuresets.
    """


