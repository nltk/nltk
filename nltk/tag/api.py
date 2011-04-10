# Natural Language Toolkit: Tagger Interface
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interface for tagging each token in a sentence with supplementary
information, such as its part of speech.
"""

from nltk.internals import overridden
from nltk.metrics import accuracy as _accuracy
from util import untag

class TaggerI(object):
    """
    A processing interface for assigning a tag to each token in a list.
    Tags are case sensitive strings that identify some property of each
    token, such as its part of speech or its sense.

    Some taggers require specific types for their tokens.  This is
    generally indicated by the use of a sub-interface to C{TaggerI}.
    For example, I{featureset taggers}, which are subclassed from
    L{FeaturesetTaggerI}, require that each token be a I{featureset}.

    Subclasses must define:
      - either L{tag()} or L{batch_tag()} (or both)
    """
    def tag(self, tokens):
        """
        Determine the most appropriate tag sequence for the given
        token sequence, and return a corresponding list of tagged
        tokens.  A tagged token is encoded as a tuple C{(token, tag)}.

        @rtype: C{list} of C{(token, tag)}
        """
        if overridden(self.batch_tag):
            return self.batch_tag([tokens])[0]
        else:
            raise NotImplementedError()

    def batch_tag(self, sentences):
        """
        Apply L{self.tag()} to each element of C{sentences}.  I.e.:

            >>> return [self.tag(sent) for sent in sentences]
        """
        return [self.tag(sent) for sent in sentences]

    def evaluate(self, gold):
        """
        Score the accuracy of the tagger against the gold standard.
        Strip the tags from the gold standard text, retag it using
        the tagger, then compute the accuracy score.

        @type gold: C{list} of C{list} of C{(token, tag)}
        @param gold: The list of tagged sentences to score the tagger on.
        @rtype: C{float}
        """

        tagged_sents = self.batch_tag([untag(sent) for sent in gold])
        gold_tokens = sum(gold, [])
        test_tokens = sum(tagged_sents, [])
        return _accuracy(gold_tokens, test_tokens)

    def _check_params(self, train, model):
        if (train and model) or (not train and not model):
            raise ValueError('Must specify either training data or trained model.')
        
class FeaturesetTaggerI(TaggerI):
    """
    A tagger that requires tokens to be I{featuresets}.  A featureset
    is a dictionary that maps from I{feature names} to I{feature
    values}.  See L{nltk.classify} for more information about features
    and featuresets.
    """

    
class HiddenMarkovModelTaggerTransformI(object):
    """
    An interface for a transformation to be used as the transform parameter
    of C{HiddenMarkovModelTagger}.
    """
    def __init__(self):
        if self.__class__ == HiddenMarkovModelTaggerTransformI:
            raise AssertionError, "Interfaces can't be instantiated"      

    def transform(self, labeled_symbols):
        """
        @return: a C{list} of transformed symbols
        @rtype: C{list}
        @param labeled_symbols: a C{list} of labeled untransformed symbols, 
            i.e. symbols that are not (token, tag) or (word, tag)
        @type labeled_symbols: C{list}
        """      
        raise NotImplementedError()
