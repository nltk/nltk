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
#{ Classification Interfaces
##//////////////////////////////////////////////////////

class ClassifierI:
    """
    A processing interface for labeling tokens with a single category
    label (or X{class}).  Labels are typically C{string}s or
    C{integer}s, but can be any immutable type.  The set of labels
    that the classifier chooses from must be fixed and finite.

    Subclasses must define:
      - L{labels()}
      - either L{classify()} or L{batch_classify()} (or both)
      
    Subclasses may define:
      - either L{probdist()} or L{batch_probdist()} (or both)
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()

    def classify(self, featureset):
        """
        @return: the most appropriate label for the given featureset.
        @rtype: label
        """
        if (self.batch_classify.im_func is not
            ClassifierI.batch_classify.im_func):
            return self.batch_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def probdist(self, featureset):
        """
        @return: a probability distribution over labels for the given
            featureset.
        @rtype: L{ProbDist <nltk.probability.ProbDist>}
        """
        if (self.batch_probdist.im_func is not
            ClassifierI.batch_probdist.im_func):
            return self.batch_probdist([featureset])[0]
        else:
            raise NotImplementedError()

    def batch_classify(self, featuresets):
        """
        Apply L{self.classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.classify(fs) for fs in featuresets]

        @rtype: C{list} of I{label}
        """
        return [self.classify(fs) for fs in featuresets]

    def batch_probdist(self, featuresets):
        """
        Apply L{self.probdist()} to each element of C{featuresets}.  I.e.:

            >>> return [self.probdist(fs) for fs in featuresets]

        @rtype: C{list} of L{ProbDist <nltk.probability.ProbDist>}
        """
        return [self.probdist(fs) for fs in featuresets]

class MultiClassifierI:
    """
    A processing interface for labeling tokens with zero or more
    category labels (or X{labels}).  Labels are typically C{string}s
    or C{integer}s, but can be any immutable type.  The set of labels
    that the multi-classifier chooses from must be fixed and finite.

    Subclasses must define:
      - L{labels()}
      - either L{classify()} or L{batch_classify()} (or both)
      
    Subclasses may define:
      - either L{probdist()} or L{batch_probdist()} (or both)
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def classify(self, featureset):
        """
        @return: the most appropriate set of labels for the given featureset.
        @rtype: C{set} of I{label}
        """
        if (self.batch_classify.im_func is not
            ClassifierI.batch_classify.im_func):
            return self.batch_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def probdist(self, featureset):
        """
        @return: a probability distribution over sets of labels for the
            given featureset.
        @rtype: L{ProbDist <nltk.probability.ProbDist>}
        """
        if (self.batch_probdist.im_func is not
            ClassifierI.batch_probdist.im_func):
            return self.batch_probdist([featureset])[0]
        else:
            raise NotImplementedError()

    def batch_classify(self, featuresets):
        """
        Apply L{self.classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.classify(fs) for fs in featuresets]
            
        @rtype: C{list} of (C{set} of I{label})
        """
        return [self.classify(fs) for fs in featuresets]

    def batch_probdist(self, featuresets):
        """
        Apply L{self.probdist()} to each element of C{featuresets}.  I.e.:

            >>> return [self.probdist(fs) for fs in featuresets]
            
        @rtype: C{list} of L{ProbDist <nltk.probability.ProbDist>}
        """
        return [self.probdist(fs) for fs in featuresets]

# # [XX] IN PROGRESS:
# class SequenceClassifierI:
#     """
#     A processing interface for labeling sequences of tokens with a
#     single category label (or X{class}).  Labels are typically
#     C{string}s or C{integer}s, but can be any immutable type.  The set
#     of labels that the classifier chooses from must be fixed and
#     finite.
#     """
#     def labels(self):
#         """
#         @return: the list of category labels used by this classifier.
#         @rtype: C{list} of (immutable)
#         """
#         raise NotImplementedError()

#     def probdist(self, featureset):
#         """
#         Return a probability distribution over labels for the given
#         featureset.
        
#         If C{featureset} is a list of featuresets, then return a
#         corresponding list containing the probability distribution
#         over labels for each of the given featuresets, where the
#         M{i}th element of this list is the most appropriate label for
#         the M{i}th element of C{featuresets}.
#         """
#         raise NotImplementedError()

#     def classify(self, featureset):
#         """
#         Return the most appropriate label for the given featureset.
        
#         If C{featureset} is a list of featuresets, then return a
#         corresponding list containing the most appropriate label for
#         each of the given featuresets, where the M{i}th element of
#         this list is the most appropriate label for the M{i}th element
#         of C{featuresets}.
#         """
#         raise NotImplementedError()

