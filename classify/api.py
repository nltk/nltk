# Natural Language Toolkit: Classifier Interface
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Interfaces for labeling tokens with category labels (or X{class
labels}).

L{ClassifierI} is a standard interface for X{single-category
classification}, in which:

    - There set of categories is known.
    - The number of categories is finite.
    - Each text belongs to exactly one category.

L{MultiClassifierI} is a standard interface for C{multi-category
classification}, in which:

    - There set of categories is known.
    - The number of categories is finite.
    - Each text belongs to zero or more categories.
"""

##//////////////////////////////////////////////////////
#{ Classifier Interfaces
##//////////////////////////////////////////////////////

class ClassifierI:
    """
    A processing interface for labeling tokens with a single category
    label (or X{class}).  Labels are typically C{string}s or
    C{integer}s, but can be any immutable type.  The set of labels
    that the classifier chooses from must be fixed and finite.
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def classify(self, token_features):
        """
        @return: The most appropriate label for a token with the given
            features.
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        """
        raise NotImplementedError()

    def label_probs(self, token_features):
        """
        @return: A probability distribution over the posssible labels
        for a token with the given features.  This method is not
        implemented by all classifiers.
        
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        @rtype: L{ProbDistI}
        """
        raise NotImplementedError()

    def label_scores(self, token_features):
        """
        @return: A dictionary mapping from possible labels for a
        token with the given features to numeric scores.  This method
        is not implemented by all classifiers.
        
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        @rtype: C{dict}
        """
        raise NotImplementedError()

class MultiClassifierI:
    """
    A processing interface for labeling tokens with zero or more
    category labels (or X{labels}).  Labels are typically C{string}s
    or C{integer}s, but can be any immutable type.  The set of labels
    that the multi-classifier chooses from must be fixed and finite.
    
    Typically, multi-classifier labels encode specific
    multi-classifier models; but do not include the algorithms for
    training the multi-classifiers.  Instead,
    L{MultiClassifierTrainer}s are used to generate classifiers from
    training data.
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def classify(self, token_features):
        """
        @return: The most appropriate set of labels for a token with
            the given features.
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        """
        raise NotImplementedError()

    def label_probs(self, token_features):
        """
        @return: A probability distribution over the posssible sets of
        labels for a token with the given features.  This method is
        not implemented by all classifiers.
        
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        @rtype: L{ProbDistI}
        """
        raise NotImplementedError()

    def label_scores(self, token_features):
        """
        @return: A dictionary mapping from possible sets of labels
        for a token with the given features to numeric scores.  This
        method is not implemented by all classifiers.
        
        @param token_features: A feature dictionary describing the
            relevant features of the token.
        @rtype: C{dict}
        """
        raise NotImplementedError()

