# Natural Language Toolkit: Detect Features
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (porting)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Functions for detecting a token's X{features}.  Features are stored in
a dictionary which maps feature names to feature values.

(Not yet ported from NLTK: A X{feature encoder} can then be used to
translate the feature dictionary into a homogenous representation
(such as a sparse boolean list), suitable for use with other
processing tasks.)
"""

def feature(functions):
    """
    Return a feature detector that applies the supplied functions
    to each token.

    @type functions: dictionary of functions
    @param properties: one or more functions in one string argument to compute
    the features.
    """
        
    return lambda tokens: [(feature,function(tokens)) for
                           (feature, function) in functions.items()]


def get_features(str):
    """
    takes a string
    returns a list of tuples (feature type, feature value)
    """


def text_feature():
    return feature({'text': lambda t:t})

def stem_feature(stemmer):
    return feature({'stem': stemmer})

# def context_feature():
# Meet the need that motivated BagOfContainedWordsFeatureDetector
# and SetOfContainedWordsFeatureDetector


######################################################################
## Demo
######################################################################

def demo():
    from nltk.corpus import brown
    from nltk import detect

    detector = detect.feature({'initial': lambda t:[t[0]],
                               'len': lambda t:[len(t)]})

    for sent in brown.words('a')[:10]:
        print detector(sent)

if __name__ == '__main__': demo()
