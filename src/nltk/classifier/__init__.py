# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""


  - Feature

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
##  Contents
##//////////////////////////////////////////////////////

# Labeled texts
#     - Texts and Labels
#     - LabeledText
#
# Features
#     - Features: Terminology Notess
#     - Feature Values
#     - Feature Detectors
#     - Feature Detector Lists
#     - Feature Value Lists
#
# Classifiers
#     - Classifiers
#     - Classifier Factories
#
# Feature Selection

# note to self: move classifiers above features at some point?  The
# classifier interfaces don't depend on features.

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
# encoded using detectors.  Also, features have unique ids.
# These ids are used to keep track of which feature value goes
# with which feature.
#
#     - A feature id is a bounded non-negative integer, which
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
##  Feature Detector Lists
##//////////////////////////////////////////////////////

class FeatureDetectorListI:
    """
    A list of the C{FeatureDetector}s that correspond to a particular
    set of features.

    Each feature is identified by a unique X{feature id}.  Feature ids
    are bounded nonnegative integers.

    A feature detector's position in the feature detector list is
    given by its feature's id.  In other words, if M{f} is a feature
    with id {i}, then M{f}'s detector is the M{i}th element of the
    feature detector list.

    If a feature detector list contains M{N} feature detectors, then
    their features' ids are M{0...N-1}.  Thus, M{N} is the length of
    the feature detector list.

    Note that feature id's are defined with respect to a feature
    detector list.  In particular, if a single feature appears in
    multiple feature detector lists, it might have different feature
    ids in each list.  Thus, care should be taken not to mix feature
    ids from different feature detector lists.
    
    Feature detector lists can be used to detect the feature values of
    each feature for a given C{LabeledText}; the resulting feature
    values are returned as a C{FeatureValueList}.  This can be
    signifigantly more efficient than individually applying each
    feature detector, since many feature detectors are closely related
    to each other.
    
    Feature detector lists can be combined using the addition
    operator.
    """

    def __getitem__(self, feature_id):
        """
        @return: the feature detector for the feature with the given
            id. 
        @rtype: C{FeatureDetectorI}
        
        @type feature_id: C{int}
        """
        raise NotImplementedError()

    def detect(self, instance):
        """
        @return: the feature ids for the features that apply to
            C{instance}.
        @rtype: C{FeatureValueListI}
        """
        raise NotImplementedError()

    def __len__(self):
        """
        @return: the number of features generated by this feature
            detector list.  The feature ids for the features in this
            feature detector list are the integers M{i}, where M{0 <=
            i < C{len(self)}}.
        @rtype: C{int}
        """
        raise NotImplementedError()

    def __add__(self, other):
        """
        @return: a new feature detector list containing the features
            from this feature detector list and from the other feature
            detector list.
        @rtype: C{FeatureDetectorListI}
        @param other: The feature detector list which should be
            combined with this feature detector list.
        @type other: C{FeatureDetectorListI}
        """
        raise NotImplementedError()

class AbstractFeatureDetectorList(FeatureDetectorListI):
    """
    Provide default definitions for most C{FeatureDetectorListI}
    methods.  The only methods you need to implement yourself are
    C{detect} and C{__len__}.
    """
    def __getitem__(self, feature_id):
        if feature_id >= len(self):
            raise IndexError('FeatureDetectorList index out of range')
        def pred(instance, detect=self.detect, id=feature_id):
            return id in detect(instance)
        return PredEvent(pred)

    def __add__(self, other):
        # n.b.: Slight circular dependency
        return MergedFeatureDetectorList(self, other)

    def __repr__(self):
        """
        @return: A string representation of this feature detector
            list, of the form::

                <FeatureDetectorList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureDetectorList with %d features>" % len(self)

class MergedFeatureDetectorList(AbstractFeatureDetectorList):
    """
    A feature list that merges the features from two or more sublists.

    @type _sub_fdlists: C{list} of C{FeatureDetectorListI}
    @ivar _sub_fdlists: The feature detector lists contained by this
        C{MergedFeatureDetectorList}.

    @type _offsets: C{list} of C{int}
    @ivar _offsets: The offset at which each feature detector list
        begins.  The final element is the length of the complete 
        C{MergedFeatureDetectorList}.
    """
    def __init__(self, *sub_fdlists):
        """
        Construct a new feature detector list, containing the features
        from each of the feature detector lists in C{sub_fdlists}.
        """
        self._sub_fdlists = []
        self._offsets = []
        offset = 0
        for sublist in sub_fdlists:
            if isinstance(sublist, MergedFeatureDetectorList):
                self._sub_fdlists += sublist._sub_fdlists
                self._offsets += [x+offset for x in sublist._offsets]
            else:
                self._sub_fdlists.append(sublist)
                self._offsets.append(offset)
            offset += len(sublist)

        # Append the final offset (the length of this
        # MergedFeatureDetectorList). 
        self._offsets.append(offset)

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._offsets[-1]

    # !!!!!! THIS IS BROKEN NOW !!!!!!!!
    def detect(self, instance):
        # Inherit docs from FeatureDetectorListI
        fnums = []
        for i in range(len(self._sub_fdlists)):
            fnums += [fnum+self._offsets[i] for fnum
                      in self._sub_fdlists[i].detect(instance)]
        return tuple(fnums)

class AlwaysFeatureDetectorList(AbstractFeatureDetectorList):
    """
    A feature list containing a single feature, which is always on.
    """
    def __init__(self): pass
    def __len__(self): return 1
    def detect(self, instance): return (0,)

class FunctionFeatureDetectorList(AbstractFeatureDetectorList):
    """
    A feature detector list constructed from a function.  The feature
    detector list contains one feature for each value in the range of
    the function.  This feature will return true iff the function
    returns that value, when applied to a C{LabeledText}.
    """
    def __init__(self, function, range):
        """
        Construct a new function-based feature detector list.

        @type function: C{LabeledTex} -> C{Boolean}
        @param function: The function on which this feature detector
            list is based.
        @type range: C{list}
        @param range: The range of C{function}; if C{function} returns
            a value outside this range, then all features will be
            false. 
        """
        self._function = function

        self._map = {}
        i = 0
        for elt in range:
            if not self._map.has_key(elt):
                self._map[elt] = i
                i += 1

        self._N = i

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, instance):
        # Inherit docs from FeatureDetectorListI
        feature = self._map.get(self._function(instance), None)
        if feature is None: return ()
        else: return (feature,)

class ValueFeatureDetectorList(FunctionFeatureDetectorList):
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
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, instance):
        # Inherit docs from FeatureDetectorListI
        feature = self._map.get(instance, None)
        if feature is None: return ()
        else: return (feature,)

##//////////////////////////////////////////////////////
##  Feature Value Lists
##//////////////////////////////////////////////////////

class FeatureValueListI:
    """
    A list of the feature values for a particular C{LabeledText}.

    Feature values can be any immutable object.  Typically, feature
    values are booleans (1 or 0); integers; or floats.

    Each feature value corresponds to a single feature; a feature
    value's position in the list is given by its feature's id.  In
    other words, if M{f} is a feature with id {i}, then M{f}'s
    value is the M{i}th element of the feature value list.
    
    If a feature value list contains M{N} feature values, then their
    features' ids are M{0...N-1}.  Thus, M{N} is the length of the
    feature value list.

    Feature value lists are typically generated by feature detector
    lists.  The feature id's are defined with respect to these feature
    detector lists.  Therefore, you should never compare feature value
    lists that were produced by different feature detector lists.

    Feature value lists can be used to efficiently iterate over sparse
    sets of feature values.  The C{assignments} method returns a list
    specifying the feature values for each feature which was not
    assigned the "default" value (typically 0).

    @see: C{FeatureDetectorListI}
    """
    def __getitem__(self):
        """
        @return: the feature value for the feature with the given id.
        @rtype: (immutable)
        """
        raise NotImplementedError()
    
    def default(self):
        """
        @return: the default value for this feature value list.  If a
            feature's value is not returned by C{assignments()},
            then that feature's value is the default value.
        @rtype: (immutable)
        """
        raise NotImplementedError()

    def __len__(self):
        """
        @return: the number of features whose values are specified by
            this feature detector list.  The feature ids for the
            features in this feature value list are the integers M{i},
            where M{0 <= i < C{len(self)}}.
        @rtype: C{int}
        """
        raise NotImplementedError()

    def assignments(self):
        """
        @return: a list of the feature value assignments for each
            feature in this feature value list whose value is not the
            default value.  These assignments are returned as a
            sequence of C{(id, value)} pairs.  The following code
            demonstrates the typical usage pattern for this method::

                for (id, value) in feature_values.assignments():
                    print "Feature %d has value %s" % (id, val)

        @rtype: sequence of (tuple of C{int} and (immutable))
        """

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

