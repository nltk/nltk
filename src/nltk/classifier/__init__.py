# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Processing classes and interfaces for labeling tokens with category
labels (or X{classes}).  Typically, classes are represented with
strings (such as C{'health'} or C{'sports'}); but other immutable
types (such as integers) can be used.  Classifiers can be used to
perform a wide range of classification tasks.  For example,
classifiers can be used...

  - to classify documents by topic.
  - to classify words by part of speech.
  - to classify acoustic signals by which phoneme they represent.
  - to classify sentences by their author.

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

The L{ClassifierTrainerI} and L{MultiClassifierTrainerI} classes
define standard interfaces for classifier trainers, which build
new classifiers from a given set of training data.

@group Classifier Interfaces: ClassifierI, MultiClassifierI
@group Classifier Trainer Interfaces: ClassifierTrainerI,
       MultiClassifierTrainerI
@group Helper Functions: attested_classes

@todo: Add raw_classify methods.
"""

from nltk.token import Token
from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
import math, Numeric, types, sets

##//////////////////////////////////////////////////////
##  Classifier Interfaces
##//////////////////////////////////////////////////////

class ClassifierI:
    """
    A processing interface for labeling tokens with a single category
    label (or X{class}).  Classes are typically C{string}s or
    C{integer}s, but can be any immutable type.  The set of classes
    that the classifier chooses from must be fixed and finite.
    
    Typically, C{ClassifierI} subclasses encode specific classifier
    models; but do not include the algorithms for training the
    classifiers.  Instead, L{ClassifierTrainer}s are used to generate
    classifiers from training data.

    @outprop: C{CLASS}: The token's class.
    @outprop: C{CLASS_PROBS}: A probability distribution over the
              token's possible classes (optional).
    @outprop: C{CLASS_SCORES}: A dictionary mapping each of the
              token's possible classes to a numeric score (optional).
    @outprop: C{CLASS_NBEST}: A list of the most likely classes for
              the token, sorted in descending order of likelihood
              (optional).
    """
    def classes(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def classify(self, token, nbest=None):
        """
        Determine which class is most appropriate for the given token,
        and output it to the C{CLASS} property.  

        If this classifier is probabilistic, then output a probability
        distribution over the possible classes for C{token} to
        C{CLASS_PROB}.

        If this classifier can generate scores, then output a
        dictionary mapping each of C{token}'s possible classes to a
        numeric score to C{CLASS_SCORES}.

        If this classifier can generate ranked output, then output a
        list of the C{nbest} most likely classes for the token, sorted
        in descending order of likelihood, to C{CLASS_NBEST}.  If
        C{nbest==None}, then include all possible classes.
        
        @type token: L{Token}
        @param token: The token whose text should be classified.
        @type nbest: C{int} or C{None}
        @param nbest: The number of classes that should be output to
            the C{CLASS_NBEST} property (if this classifier can
            generate ranked output).  If C{nbest=None}, then output
            all possible classes.
        """
        raise NotImplementedError()

class MultiClassifierI:
    """
    A processing interface for labeling tokens with zero or more
    category labels (or X{classes}).  Classes are typically C{string}s
    or C{integer}s, but can be any immutable type.  The set of classes
    that the multi-classifier chooses from must be fixed and finite.
    
    Typically, multi-classifier classes encode specific
    multi-classifier models; but do not include the algorithms for
    training the multi-classifiers.  Instead,
    L{MultiClassifierTrainer}s are used to generate classifiers from
    training data.

    @outprop: C{CLASSES}: The set of classes that describe the token
              (encoded with C{tuple} or L{Set<sets.Set>}).
    @outprop: C{CLASSES_PROBS}: A probability distribution over the
              token's possible sets of classes (optional).
    @outprop: C{CLASSES_SCORES}: A dictionary mapping each of the
              token's possible sets of classes to a numeric score
              (optional).
    @outprop: C{CLASSES_NBEST}: A list of the most likely sets of
              classes for the token, sorted in descending order of
              likelihood (optional).
    """
    def classes(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise NotImplementedError()
    
    def classify(self, token, nbest=None):
        """
        Determine the most appropriate set of classes for the given
        token, and output it to the C{CLASSES} property (encoded with
        C{tuple} or L{Set<sets.Set>}).

        If this classifier is probabilistic, then output a probability
        distribution over the possible sets of classes for C{token} to
        C{CLASSES_PROB}.

        If this classifier can generate scores, then output a
        dictionary mapping each of C{token}'s possible sets of classes
        to a numeric score to C{CLASSES_SCORES}.

        If this classifier can generate ranked output (and
        C{nbest!=0}), then output a list of the C{nbest} most likely
        sets of classes for the token, sorted in descending order of
        likelihood, to C{CLASSES_NBEST}.  If C{nbest==None}, then
        include all possible sets of classes.
        
        @type token: L{Token}
        @param token: The token whose text should be classified.
        @type nbest: C{int} or C{None}
        @param nbest: The number of sets of classes that should be
            output to the C{CLASSES_NBEST} property (if this classifier
            can generate ranked output).  If C{nbest=None}, then
            output all possible sets of classes.
        """
        raise NotImplementedError()

##//////////////////////////////////////////////////////
##  Classifier Trainer Interfaces
##//////////////////////////////////////////////////////

class ClassifierTrainerI:
    """
    A processing interface for constructing new classifiers from
    training data.

    @inprop: C{CLASS}: The token's class.
    """
    def train(self, training_tokens, classes=None):
        """
        Train a new classifier, based on the given training tokens.

        @type training_tokens: C{list} of C{Token}
        @param training_tokens: The list of classified tokens that the
            new classifier should be based on.  Each token in this
            list must define the C{CLASS} property.
        @param classes: The set of possible classes.  If C{classes} is 
            not specified, then the set of classes attested in the
            training data will be used.
        @type classes: C{list} of (immutable)
        @return: A new classifier, trained from the given classified
            tokens.
        @rtype: C{ClassifierI}
        """
        raise NotImplementedError()

class MultiClassifierTrainerI:
    """
    A processing interface for constructing new multi-classifiers from
    training data.

    @inprop: C{CLASS}: The token's class.
    """
    def train(self, training_tokens, classes=None):
        """
        Train a new multi-classifier, based on the given training
        tokens.

        @type training_tokens: C{list} of C{Token}
        @param training_tokens: The list of classified tokens that the
            new multi-classifier should be based on.  Each token in
            this list must define the C{CLASSES} property.
        @param classes: The set of possible classes.  If C{classes} is 
            not specified, then the set of classes attested in the
            training data will be used.
        @type classes: C{list} of (immutable)
        @return: A new multi-classifier, trained from the given
            classified tokens.
        @rtype: C{MultiClassifierI}
        """
        raise NotImplementedError()

##//////////////////////////////////////////////////////
##  Helper Functions
##//////////////////////////////////////////////////////

def attested_classes(tokens):
    """
    @return: A list of all classes that are attested in the given list
        of tokens.
    @rtype: C{list} of (immutable)
    @param tokens: The list of tokens from which to extract classes.
    @type tokens: C{list} of (C{Token} with type C{ClassedText})
    """
    assert _chktype(1, tokens, [Token], (Token,))
    return list(sets.Set([token['CLASS'] for token in tokens]))

