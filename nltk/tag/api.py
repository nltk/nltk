# Natural Language Toolkit: Tagger Interface
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Interface for tagging each token in a sentence with supplementary
information, such as its part of speech.
"""

from new import function
from types import MethodType, LambdaType, FunctionType
from marshal import dumps, loads

from nltk.internals import overridden

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

            >>> return [self.tag(tokens) for tokens in sentences]
        """
        return [self.tag(tokens) for tokens in sentences]

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
        
    def transform(self, symbols):
        """
        @return: a C{list} of transformed symbols
        @rtype: list
        @param symbols: a C{list} of symbols
        @type symbols: list
        """      
        raise NotImplementedError

    def __getstate__(self):
        state = self.__dict__
        state['_lambda_functions'] = {}
        state['_instance_methods'] = {}
        for name, attr in state.items():
            if isinstance(attr, LambdaType) and attr.__name__ == '<lambda>':
                state['_lambda_functions'][name] = dumps(attr.func_code)
                del state[name]
            elif isinstance(attr, MethodType):
                state['_instance_methods'][name] = \
                    (attr.im_self, attr.im_func.func_name)
                del state[name]
        return state
    
    def __setstate__(self, state):
        for name, mcode in state.get('_lambda_functions', {}).items():
            state[name] = function(loads(mcode), {})
        if '_lambda_functions' in state:
            del state['_lambda_functions']
        for name, (im_self, im_func_name) \
        in state.get('_instance_methods', {}).items():
            state[name] = getattr(im_self, im_func_name)
        if '_instance_methods' in state:
            del state['_instance_methods']
        self.__dict__ = state      
