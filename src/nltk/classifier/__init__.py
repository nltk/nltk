# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Classes and interfaces used to classify texts into categories.

  - A category is typicaly a string or an integer
  - A categorized document is represented with a TaggedType.  The base
    type is the text, and the tag is the category.

Classes/Interfaces:
  - FeatureListI: abstract specification of a list of features
  - ClassifierI: abstract specification of a classifier
    - NBClassifier: naive bayes classifier
    - MaxentClassifier: maxent classifier
  - ClassifierFactory: constructs a classifier

Sub-modules:
  - naivebayes
  - maxent

Picture::


      unlabeled_text --> ClassifierI --> labeled_text
                             ^
                             |
    labeled_text[] --> ClassifierFactoryI
                             ^
                             |
                        FeatureListI    

"""

##//////////////////////////////////////////////////////
##  Texts and Labels
##//////////////////////////////////////////////////////

# A text can be any object.  In theory, texts are required to be
# immutable, since they are used as the type of a token.  However, in
# practice, nothing currently depends on their being immutable.  Thus,
# lists of words can currently be used (instead of tuples of words).

# A label can be any immutable object.  Typically, labels are either
# integers or strings.

##//////////////////////////////////////////////////////
##  LabeledTexts
##//////////////////////////////////////////////////////

class LabeledText:
    """
    A type consisting of a text and a label.  A typical example would
    be a document labeled with a category, such as "sports".

    The text and the label are both required to be immutable.  For
    many applications, texts are strings or tuples of strings; and
    labels are strings or integers.

    @type _text: (any)
    @ivar _text: The text type of the C{LabeledType}.  This represents
        the type that is labeled.
    @type _label: (any)
    @ivar _label: The text type's label.  This provides information about
        the text type, such as its part-of-speech.
    """
    def __init__(self, text, label):
        """
        Construct a new C{LabeledType}

        @param text: The new C{LabeledType}'s text.
        @type text: (any immutable type)
        @param label: The new C{LabeledType}'s label.
        @type label: (any immutable type)
        """
        self._text = text
        self._label = label
        
    def text(self):
        """
        @return: this C{LabeledType}'s text.
        @rtype: (immutable)
        """
        return self._text
    
    def label(self):
        """
        @return: this C{LabeledType}'s label.
        @rtype: (immutable)
        """
        return self._label
    
    def __eq__(self, other):
        """
        @return: true if this C{LabeledType} is equal to C{other}.  In
            particular, return true iff C{other} is a C{LabeledType},
            C{self.text()==other.text()}, and
            C{self.label()==other.label()}; return false otherwise.
        @rtype: C{boolean}
        """
        if not isinstance(other, LabeledType):
            return 0
        return (self._text == other._text and
                self._label == other._label)

    def __ne__(self, other):
        """
        @return: false if this C{LabeledType} is equal to C{other}.  In
            particular, return false iff C{other} is a C{LabeledType},
            C{self.text()==other.text()}, and
            C{self.label()==other.label()}; return true otherwise.
        @rtype: C{boolean}
        """
        return not (self == other)
    
    def __hash__(self):
        return hash( (self._text, self._label) )
    
    def __repr__(self):
        """
        @rtype: string
        """
        return "%r/%r" % (self._text, self._label)



##//////////////////////////////////////////////////////
##  Features: Terminology notes.
##//////////////////////////////////////////////////////

# To make my terminology precise, I'll give tentative definitions
# here:
# 
#     - A "feature" specifies some aspect of LabeledTexts.  This is an
#       abstract aspect, not a particular value.  An example would be
#       "the first letter of a word", but not "a".
#     - A "feature value" specifies the value of a feature for a
#       particular LabeledText.  An example would be "a."
#     - A "feature detector" is an object that can be used to find
#       the value of a feature for a particular LabeledText.  In
#       otherwords, a feature detector conceptually maps LabeledTexts
#       to feature values.
#
# Features are not directly represented; instead, they are indirectly
# encoded using detectors.  Also, features have unique identifiers.
# These identifiers are used to keep track of which feature value goes
# with which feature.
#
#     - A feature identifier is a bounded non-negative integer, which
#       uniquely identifies a single feature.
#
# Alternatively, I could have a "Feature" class that has the following
# accessor functions:
#
#     - id()
#     - detector()
#
# But I don't think that's necessary.

##//////////////////////////////////////////////////////
##  Feature Values
##//////////////////////////////////////////////////////

# As noted above in "Features: Terminology notes," feature values can
# be any immutable type.  Typically, feature values are booleans,
# integers, or floats.

##//////////////////////////////////////////////////////
##  Feature Detectors
##//////////////////////////////////////////////////////

#
# Feature detectors are almost never used directly.  Instead,
# FeatureDetectorLists are used, which efficiently encode large sets
# of feature detectors.  FeatureDetectorLists can apply a large number
# of features to a single LabeledText at once.
#

class FeatureDetectorI:
    """
    A X{feature detector} is used to find the value of a single
    feature for any C{LabeledText}.  A X{feature} is an aspect of
    C{LabeledText}s.  A typical example of a feature is:

      - Whether a document contains the word "neural" and has the
        label "medical."

    If a feature detector for this feature were applied to a
    C{LabeledText}, it would return 1 if the text contains the word
    "neural" and has the label "medical;" and 0 otherwise.

    Feature detectors are applied to C{LabeledText}s using the
    C{detect} method.
    """
    def detect(self, labeled_text):
        """
        @return: this feature's value for the given labeled text.
        @rtype: C{any}
        """

class FunctionFeatureDetector(FeatureDetectorI):
    """
    A feature detector that uses a given function to find the value of
    a single feature for any C{LabeledText}.  When a
    C{FunctionFeatureDetector} with function M{f} is applied to a
    labeled text M{lt}, it will return M{f(lt)}.
    """
    def __init__(self, func, name=None):
        """
        Construct a new C{FunctionFeatureDetector} from the given
        function.  
        """
        self._name = name
        self._func = func

    def detect(self, labeled_text):
        return self._func(labeled_text)

    def __repr__(self):
        if self._name is None:
            self._name = self._func.__name__+'(lt)'
        return "<FeatureDetector: %s>" % self._func.__name__

##//////////////////////////////////////////////////////
##  Feature Lists
##//////////////////////////////////////////////////////

class FeatureListI:
    """
    A list of features.
    """

    def __getitem__(self, feature_id):
        """
        @return: the feature with the given identifier.  A feature is
            an event containing categorized documents.
        @rtype: C{EventI}
        
        @type feature_id: C{int}
        """
        raise NotImplementedError()

    def detect(self, instance):
        """
        @return: the feature identifiers for the features that apply to
            C{instance}.
        @rtype: C{list} of C{int}
        """
        raise NotImplementedError()

    def __len__(self):
        """
        @return: the number of features generated by this feature list.
        @rtype: C{int}
        """
        raise NotImplementedError()

    def __add__(self, other):
        """
        @return: a new feature list containing the features from this
        feature list and from the other feature list.
        """
        raise NotImplementedError()

class AbstractFeatureList(FeatureListI):
    """
    Provide default definitions for most C{FeatureListI} methods.  The
    only methods you need to implement yourself are C{detect} and
    C{__len__}.
    """

    def __getitem__(self, feature_id):
        # Inherit docs from FeatureListI
        if feature_id >= len(self):
            raise IndexError('FeatureList index out of range')
        def pred(instance, detect=self.detect, id=feature_id):
            return id in detect(instance)
        return PredEvent(pred)

    def __add__(self, other):
        # Inherit docs from FeatureListI
        # n.b.: Slight circular dependency
        return MergedFeatureList(self, other)

    def __repr__(self):
        return "<FeatureList with %d features>" % len(self)

class MergedFeatureList(AbstractFeatureList):
    """
    A feature list that merges the features from two or more sublists.
    """
    def __init__(self, *sublists):
        self._sublists = []
        self._offsets = []
        offset = 0
        for sublist in sublists:
            if isinstance(sublist, MergedFeatureList):
                self._sublists += sublist._sublists
                self._offsets += [x+offset for x in sublist._offsets]
            else:
                self._sublists.append(sublist)
                self._offsets.append(offset)
            offset += len(sublist)

    def __len__(self):
        # Inherit docs from FeatureListI
        return self._offsets[-1]+len(self._sublists[-1])

    def detect(self, instance):
        # Inherit docs from FeatureListI
        fnums = []
        for i in range(len(self._sublists)):
            fnums += [fnum+self._offsets[i] for fnum
                      in self._sublists[i].detect(instance)]
        return tuple(fnums)

class AlwaysFeatureList(AbstractFeatureList):
    """
    A feature list containing a single feature, which is always on.
    """
    def __init__(self): pass
    def __len__(self): return 1
    def detect(self, instance): return (0,)

class FunctionFeatureList(AbstractFeatureList):
    def __init__(self, function, range):
        self._function = function

        self._map = {}
        i = 0
        for elt in range:
            if not self._map.has_key(elt):
                self._map[elt] = i
                i += 1

        self._N = i

    def __len__(self):
        # Inherit docs from FeatureListI
        return self._N

    def detect(self, instance):
        # Inherit docs from FeatureListI
        feature = self._map.get(self._function(instance), None)
        if feature is None: return ()
        else: return (feature,)

class ValueFeatureList(FunctionFeatureList):
    """
    Assign a different feature to each value in a list of values.
    E.g., this could be used to have a different feature for each word
    type.  
    """
    def __init__(self, values):
        """
        @param values: The list of possible values.  Duplicates are
            allowed, so you can just give a big list of tokens..
        @type values: list of token or list of type; I'm not sure which
        """
        self._map = {}
        i = 0
        for elt in values:
            if not self._map.has_key(elt):
                self._map[elt] = i
                i += 1

        self._N = i

    def __len__(self):
        # Inherit docs from FeatureListI
        return self._N

    def detect(self, instance):
        # Inherit docs from FeatureListI
        feature = self._map.get(instance, None)
        if feature is None: return ()
        else: return (feature,)

##//////////////////////////////////////////////////////
##  LabeledType
##//////////////////////////////////////////////////////

##//////////////////////////////////////////////////////
##  ClassiiferI
##//////////////////////////////////////////////////////

class ClassifierI:
    def classify(instance):
        """
        Classify an instance.
        
        @rtype: (ProbDist of)? (label | LabeledType)
        """

class ClassifierFactoryI:
    "???"

