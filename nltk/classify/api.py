# Natural Language Toolkit: Classifier Interface
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interfaces for labeling tokens with category labels (or X{class
labels}).

L{ClassifierI} is a standard interface for X{single-category
classification}, in which:

    - The set of categories is known.
    - The number of categories is finite.
    - Each text belongs to exactly one category.

L{MultiClassifierI} is a standard interface for C{multi-category
classification}, in which:

    - The set of categories is known.
    - The number of categories is finite.
    - Each text belongs to zero or more categories.
"""
from nltk.internals import overridden

##//////////////////////////////////////////////////////
#{ Classification Interfaces
##//////////////////////////////////////////////////////

class ClassifierI(object):
    """
    A processing interface for labeling tokens with a single category
    label (or X{class}).  Labels are typically C{string}s or
    C{integer}s, but can be any immutable type.  The set of labels
    that the classifier chooses from must be fixed and finite.

    Subclasses must define:
      - L{labels()}
      - either L{classify()} or L{batch_classify()} (or both)
      
    Subclasses may define:
      - either L{prob_classify()} or L{batch_prob_classify()} (or both)
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
        if overridden(self.batch_classify):
            return self.batch_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def prob_classify(self, featureset):
        """
        @return: a probability distribution over labels for the given
            featureset.
        @rtype: L{ProbDistI <nltk.probability.ProbDistI>}
        """
        if overridden(self.batch_prob_classify):
            return self.batch_prob_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def batch_classify(self, featuresets):
        """
        Apply L{self.classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.classify(fs) for fs in featuresets]

        @rtype: C{list} of I{label}
        """
        return [self.classify(fs) for fs in featuresets]

    def batch_prob_classify(self, featuresets):
        """
        Apply L{self.prob_classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.prob_classify(fs) for fs in featuresets]

        @rtype: C{list} of L{ProbDistI <nltk.probability.ProbDistI>}
        """
        return [self.prob_classify(fs) for fs in featuresets]

    
class MultiClassifierI(object):
    """
    A processing interface for labeling tokens with zero or more
    category labels (or X{labels}).  Labels are typically C{string}s
    or C{integer}s, but can be any immutable type.  The set of labels
    that the multi-classifier chooses from must be fixed and finite.

    Subclasses must define:
      - L{labels()}
      - either L{classify()} or L{batch_classify()} (or both)
      
    Subclasses may define:
      - either L{prob_classify()} or L{batch_prob_classify()} (or both)
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
        if overridden(self.batch_classify):
            return self.batch_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def prob_classify(self, featureset):
        """
        @return: a probability distribution over sets of labels for the
            given featureset.
        @rtype: L{ProbDistI <nltk.probability.ProbDistI>}
        """
        if overridden(self.batch_prob_classify):
            return self.batch_prob_classify([featureset])[0]
        else:
            raise NotImplementedError()

    def batch_classify(self, featuresets):
        """
        Apply L{self.classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.classify(fs) for fs in featuresets]
            
        @rtype: C{list} of (C{set} of I{label})
        """
        return [self.classify(fs) for fs in featuresets]

    def batch_prob_classify(self, featuresets):
        """
        Apply L{self.prob_classify()} to each element of C{featuresets}.  I.e.:

            >>> return [self.prob_classify(fs) for fs in featuresets]
            
        @rtype: C{list} of L{ProbDistI <nltk.probability.ProbDistI>}
        """
        return [self.prob_classify(fs) for fs in featuresets]


# # [XX] IN PROGRESS:
# class SequenceClassifierI(object):
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

#     def prob_classify(self, featureset):
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

