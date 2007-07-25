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

L{ClassifyI} is a standard interface for X{single-category
classification}, in which:

    - There set of categories is known.
    - The number of categories is finite.
    - Each text belongs to exactly one category.

L{MultiClassifyI} is a standard interface for C{multi-category
classification}, in which:

    - There set of categories is known.
    - The number of categories is finite.
    - Each text belongs to zero or more categories.
"""

##//////////////////////////////////////////////////////
#{ Classification Interfaces
##//////////////////////////////////////////////////////

class ClassifyI:
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

    def probdist(self, featureset):
        """
        Return a probability distribution over labels for the given
        featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the probability distribution
        over labels for each of the given featuresets, where the
        M{i}th element of this list is the most appropriate label for
        the M{i}th element of C{featuresets}.
        """
        raise NotImplementedError()

    def classify(self, featureset):
        """
        Return the most appropriate label for the given featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the most appropriate label for
        each of the given featuresets, where the M{i}th element of
        this list is the most appropriate label for the M{i}th element
        of C{featuresets}.
        """
        raise NotImplementedError()

class MultiClassifyI:
    """
    A processing interface for labeling tokens with zero or more
    category labels (or X{labels}).  Labels are typically C{string}s
    or C{integer}s, but can be any immutable type.  The set of labels
    that the multi-classifier chooses from must be fixed and finite.
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def probdist(self, featureset):
        """
        Return a probability distribution over sets of labels for the
        given featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the probability distribution
        over sets of labels for each of the given featuresets, where
        the M{i}th element of this list is the most appropriate set of
        labels for the M{i}th element of C{featuresets}.
        """
        raise NotImplementedError()

    def classify(self, featureset):
        """
        Return the most appropriate set of labels for the given
        featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the most appropriate set of
        labels for each of the given featuresets, where the M{i}th
        element of this list is the most appropriate set of labels for
        the M{i}th element of C{featuresets}.
        """
        raise NotImplementedError()

# [XX] IN PROGRESS:
class SequenceClassifyI:
    """
    A processing interface for labeling sequences of tokens with a
    single category label (or X{class}).  Labels are typically
    C{string}s or C{integer}s, but can be any immutable type.  The set
    of labels that the classifier chooses from must be fixed and
    finite.
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()

    def probdist(self, featureset):
        """
        Return a probability distribution over labels for the given
        featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the probability distribution
        over labels for each of the given featuresets, where the
        M{i}th element of this list is the most appropriate label for
        the M{i}th element of C{featuresets}.
        """
        raise NotImplementedError()

    def classify(self, featureset):
        """
        Return the most appropriate label for the given featureset.
        
        If C{featureset} is a list of featuresets, then return a
        corresponding list containing the most appropriate label for
        each of the given featuresets, where the M{i}th element of
        this list is the most appropriate label for the M{i}th element
        of C{featuresets}.
        """
        raise NotImplementedError()

