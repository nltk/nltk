# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for labeling tokens with category labels (or
X{class labels}).  Typically, labels are represented with strings
(such as C{'health'} or C{'sports'}).  Classifiers can be used to
perform a wide range of classification tasks.  For example,
classifiers can be used...

  - to classify documents by topic.
  - to classify ambiguous words by which word sense is intended.
  - to classify acoustic signals by which phoneme they represent.
  - to classify sentences by their author.

Features
--------
In order to decide which category label is appropriate for a given
token, classifiers examine one or more 'features' of the token.  These
X{features} are typically chosen by hand, and indicate which aspects
of the token are relevant to the classification decision.  For
example, a document classifier might use a separate feature for each
word, recording how often that word occured in the document.

Featuresets
-----------
The features describing a token are encoded using a X{featureset},
which is a dictionary that maps from X{feature names} to X{feature
values}.  Feature names are unique strings that indicate what aspect
of the token is encoded by the feature.  Examples include
C{'prevword'}, for a feature whose value is the previous word; and
C{'contains-word(library)'} for a feature that is true when a document
contains the word C{'library'}.  Feature values are typically
booleans, numbers, or strings, depending on which feature they
describe.

Featuresets are typically constructed using a X{feature
extraction function}, which takes a token as its input, and returns a
featuresets describing that token.  This feature extraction
function is applied to each token before it is fed to the classifier:

    >>> # Define a feature extraction function.
    >>> def document_features(document):
    ...     return dict([('contains-word(%s)'%w,True) for w in document])

    >>> Classify each Gutenberg document.
    >>> for file in gutenberg.files():
    ...     doc = gutenberg.tokenized(file)
    ...     print doc_name, classifier.classify(document_features(doc))

Training Classifiers
--------------------
Most classifiers are built by training them on a list of hand-labeled
examples, known as the X{training set}.  Training sets are represented
as lists of C{(featuredict, label)} tuples.
"""

from api import *
from util import *
from naivebayes import *
from decisiontree import *
from weka import *
from nltk.internals import deprecated, Deprecated

__all__ = [
    # Classifier Interfaces
    'ClassifierI', 'MultiClassifierI',
    
    # Classifiers
    'NaiveBayesClassifier', 'DecisionTreeClassifier', 'WekaClassifier',
    
    # Utility functions.  Note that accuracy() is intentionally
    # omitted -- it should be accessed as nltk.classify.accuracy();
    # similarly for log_likelihood() and attested_labels().
    'config_weka',
    
    # Demos -- not included.
    ]
    

try:
    import numpy
    from maxent import *
    __all__ += ['ConditionalExponentialClassifier', 'train_maxent_classifier',]
except ImportError:
    pass

######################################################################
#{ Deprecated
######################################################################
from nltk.internals import Deprecated
class ClassifyI(ClassifierI, Deprecated):
    """Use nltk.ClassifierI instead."""

@deprecated("Use nltk.classify.accuracy() instead.")
def classifier_accuracy(classifier, gold):
    return accuracy(classifier, gold)
@deprecated("Use nltk.classify.log_likelihood() instead.")
def classifier_log_likelihood(classifier, gold):
    return log_likelihood(classifier, gold)

