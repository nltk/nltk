# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001-2007 University of Pennsylvania
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

Feature Dictionaries
--------------------
The set of features describing a token is encoded using a X{feature
dictionary}, which maps from X{feature names} to X{feature values}.
Feature names are unique strings that indicate what aspect of the
token is encoded by the feature.  Examples include C{'prevword'}, for
a feature whose value is the previous word; and
C{'contains-word(library)'} for a feature that is true when a document
contains the word C{'library'}.  Feature values are typically
booleans, numbers, or strings, depending on which feature they
describe.

Feature dictionaries are typically constructed using a X{feature
extraction function}, which takes a token as its input, and returns a
feature dictionary describing that token.  This feature extraction
function is applied to each token before it is fed to the classifier:

    >>> # Define a feature extraction function.
    >>> def document_features(document):
    ...     return dict([('contains-word(%s)'%w,True) for w in document])

    >>> Classify each Gutenberg document.
    >>> for doc_name in gutenberg.items:
    ...     doc = gutenberg.tokenized(doc_name)
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
from maxent import *
