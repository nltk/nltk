# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classification is the task of assigning a label to a given text token.

Maybe split up as follows:
  Basics:
    __init__ -> LabeledText, ClassifierI, ClassifierTrainerI
    feature  -> FeatureValueList, FeatureDetectorList, etc.
    feature_selection -> feature selection (change name?)
  Models:
    naivebayes (paramaterized by a p. dist)
    maxent (paramaterized by a sequence of lambda's)
  Trainers:
    foo.. :)

Labeled Texts
=============

Classifiers
===========

Features
========

Feature Selection
-----------------


Random Picture
==============


      unlabeled_text --> ClassifierI --> labeled_text
                             ^
                             |
    labeled_text[] --> ClassifierTrainerI
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
# Classifiers
#     - Classifiers
#     - Classifier Factories
#
# Features
#     - Features: Terminology Notess
#     - Feature Values
#     - Feature Detectors
#     - Feature Detector Lists
#     - Feature Value Lists
#
# Feature Selection

from Numeric import array

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
        @param other: The C{LabeledText} to compare this
            C{LabeledText} with.
        @type other: C{LabeledText}
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
        @param other: The C{LabeledText} to compare this
            C{LabeledText} with.
        @type other: C{LabeledText}
        """
        return not (self == other)
    
    def __hash__(self):
        return hash( (self._text, self._label) )
    
    def __repr__(self):
        """
        @return: a string representation of this labeled text.
        @rtype: C{string}
        """
        return "%r/%r" % (self._text, self._label)


##//////////////////////////////////////////////////////
##  Classiifers & Classifier Factories
##//////////////////////////////////////////////////////

class ClassifierI:
    """
    A processing interface for assigning a label to a text.
    Classifiers are required to define one method, C{classify}, which
    determines which label is most appropriate for a given text
    token.

    Classifiers are also encouranged to implement the following
    methods:

      - C{distribution}: Returns a probability distribution over
        labeled tokens.
      - C{prob}: Returns the probability that a token has a given
        label. 

    Classes implementing the ClassifierI interface may choose to only
    support certain classes of tokens for input.  If a method is
    unable to return a correct result because it is given an
    unsupported class of token, then it should raise a
    NotImplementedError.

    Typically, classifiers encode specific classifier models; but do
    not include the algorithms for training the classifiers.  Instead,
    C{ClassifierTrainer}s are used to generate classifiers from
    training data.

    @see: C{ClassifierTrainerI}
    """
    
    def classify(unlabeled_token):
        """
        Determine which label is most appropriate for the given text
        token, and return a C{LabeledText} token constructed from the
        given text token and the chosen label.
        
        @return: a C{LabeledText} token whose label is the most
            appropriate label for the given token; whose text is the
            given token's text; and whose location is the given
            token's location.
        @rtype: C{Token} with type C{LabeledText}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: (immutable)
        """
        raise NotImplementedError()

    def distribution(unlabeled_token):
        """
        @return: a probability distribution whose samples are labeled
            tokens derived from C{unlabeled_token}.  In particular,
            the samples should be C{LabeledText} tokens whose text is
            C{unlabeled_token}'s text; and whose location is 
            C{unlabeled_token}'s location.  The probability of each
            sample indicates the likelihood that the unlabeled token
            should be assigned a given label.
        @rtype: C{ProbDistI}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: (immutable)
        """
        raise NotImplementedError()

class ClassifierTrainerI:
    """
    A processing interface for constructing new C{Classifier}s, using
    training data.
    """
    def train(labeled_tokens):
        """
        Train a new classifier, using the given training samples.

        @type labeled_tokens: C{list} of (C{Token} with type C{LabeledText})
        @param labeled_tokens: A list of correctly labeled texts.
            These texts will be used as training samples to construct
            a new classifier.

        @return: A new classifier, trained from the given labeled
            tokens.
        @rtype: C{ClassifierI}
        """

##//////////////////////////////////////////////////////
##  Features: Terminology notes.
##//////////////////////////////////////////////////////

# Many (but not necessarily all) classifiers are based on the
# following general feature framework...

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
        @param labeled_text: the labeled text whose feature value
            should be detected.
        @type labeled_text: C{LabeledText}
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
        """
        @return: a string representation of this feature detector.
        @rtype: C{string}
        """
        if self._name is None:
            self._name = self._func.__name__+'()'
        return "<FeatureDetector: %s>" % self._name

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

        @param feature_id: The id of the feature whose detector should
            be returned.  This is should be an integer M{i} such that
            M{0 <= i < N}, where M{N} is the number of features in
            this feature detector list.
        @type feature_id: C{int}
        """
        raise NotImplementedError()

    def detect(self, labeled_text):
        """
        @return: a feature value list specifying the value of each of
            feature for the given labeled text.
        @rtype: C{FeatureValueListI}
        @param labeled_text: the labeled text whose feature values
            should be detected.
        @type labeled_text: C{LabeledText}
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
        def f(labeled_text, detect=self.detect, id=feature_id):
            return id in detect(labeled_text)
        return FunctionFeatureDetector(f, ('f_%d()' % feature_id))

    def __add__(self, other):
        # n.b.: Slight circular dependency (since
        # MergedFeatureDetectorList is itself derived from
        # AbstractFeatureDetectorList).
        return MergedFeatureDetectorList(self, other)

    def __repr__(self):
        """
        @return: a string representation of this feature detector
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
        begins.
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

        self._N = offset

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    # This may not be the most efficient method if we're not using
    # feature detector lists that return SimpleFeatureValueLists.  Oh
    # well.  I'll deal with efficiency later. :)
    def detect(self, labeled_text):
        assignments = []
        for i in range(len(self._sub_fdlists)):
            offset = self._offsets[i]
            feature_values = self._sub_fdlists[i].detect(labeled_text)
            assignments += [(fnum+offset, val) for (fnum, val)
                            in feature_values.assignments()]
            
        return SimpleFeatureValueList(assignments, self._N)

class AlwaysFeatureDetectorList(AbstractFeatureDetectorList):
    """
    A feature list containing a single feature, which is always on.
    """
    def __init__(self):
        """
        Construct a new C{AlwaysFeatureDetectorList}.
        """
    def __len__(self): return 1
    def detect(self, labeled_text):
        return SimpleFeatureValueList(((0,1),), 1)

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

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        feature = self._map.get(self._function(labeled_text), None)
        if feature is None: assignments = ()
        else: assignments = ((feature, 1),)
        return SimpleFeatureValueList(assignments, self._N)

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

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        feature = self._map.get(labeled_text, None)
        if feature is None: assignments = ()
        else: assignments = ((feature, 1),)
        return SimpleFeatureValueList(assignments, self._N)

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
    def __getitem__(self, feature_id):
        """
        @return: the feature value for the feature with the given id.
        @rtype: (immutable)
        
        @param feature_id: The id of the feature whose value should
            be returned.  This is should be an integer M{i} such that
            M{0 <= i < N}, where M{N} is the number of features in
            this feature value list.
        @type feature_id: C{int}
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
            this feature value list.  The feature ids for the
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
        raise NotImplementedError()

class ArrayFeatureValueList(FeatureValueListI):
    """
    An array-bsed implementation of C{FeatureValueListI}
    """
    def __init__(self, values, default=0):
        self._values = array(values)
        self._default = default

    def __getitem__(self, feature_id):
        return self._values[feature_id]

    def default(self):
        return default

    def __len__(self):
        return len(self._values)

    def assignments(self):
        return [(i, self._values[i]) for i in range(len(self._values))]

class SimpleFeatureValueList(FeatureValueListI):
    """
    A simple list-based implementation of the C{FeatureValueListI}
    interface.

    @type _assignments: C{list} of (C{tuple} of C{int} and (immutable))
    @ivar _assignments: A list of (id, value) pairs.
    @type _len: C{int}
    @ivar _len: The number of features whose values are specified by
        this feature value list.
    @type _default: (immutable)
    @ivar _default: The default value.
    """
    def __init__(self, assignments, len, default=0):
        """
        Construct a new C{SimpleFeatureValueList}.

        @type assignments: C{list} of (C{tuple} of C{int} and (immutable))
        @param assignments: A list of the feature value assignments for
            each feature in this feature value list whose value is not
            the default value.  These assignments are specified as a
            list of C{(id, value)} pairs.
        @type len: C{int}
        @param len: The number of features whose values are specified
            by this feature value list.
        @type default: (immutable)
        @param default: The default value for this feature value list.
            If a feature's value is not specified by C{assignments},
            then that feature's value is the default value.
        """
        self._assignments = assignments
        self._len = len
        self._default = default

    def __getitem__(self, feature_id):
        if feature_id >= self._len:
            raise IndexError('FeatureValueList index out of range')
        for (id, val) in self._assignments:
            if id == feature_id:
                return val
        return self._default

    def default(self):
        return self._default

    def __len__(self):
        return self._len

    def assignments(self):
        return self._assignments

    def __repr__(self):
        """
        @return: a string representation of this feature value
            list, of the form::

                <FeatureValueList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureValueList with %d features>" % len(self)

##//////////////////////////////////////////////////////
##  Labeled FeatureValueList
##//////////////////////////////////////////////////////

class LabeledFeatureValueList:
    """
    The label and feature values that correspond to a C{LabeledText}.
    This class encapsulates all of the information about a
    C{LabeledText} that a feature-driven classifier can use.
    """
    def __init__(self, fvl, label):
        """
        Construct a new C{LabeledFeatureValueList}.
        C{LabeledFeatureValueList}s are typically constructed from
        C{LabeledText}s.  For example, the following code constructs a
        new labeled feature value list for C{labeled_text}.  It uses
        C{feature_detector_list} to produce the feature value list::

            >>> fvl = feature_detector_list.detect(labeled_text)
            >>> label = labeled_text.label()
            >>> lfvl = LabeledFeatureValueList(lfvl, label)
        
        @param fvl: The feature value list
        @type fvl: C{FeatureValueList}
        @param label: The label
        @type label: C{string}
        """
        self._fvl = fvl
        self._label = label
        
    def feature_values(self):
        """
        @return: this C{LabeledFeatureValueList}'s feature value list.
        @rtype: C{FeatureValueList}
        """
        return self._fvl
    
    def label(self):
        """
        @return: this C{LabeledFeatureValueList}'s label.
        @rtype: C{string}
        """
        return self._label
    
    def __repr__(self):
        """
        @return: a string representation of this
            C{LabeledFeatureValueList}.
        @rtype: C{string}
        """
        return '<LabeledFeatureValueList %r %r>' % (self._label, self._fvl) 

##//////////////////////////////////////////////////////
##  Feature Selection
##//////////////////////////////////////////////////////

##//////////////////////////////////////////////////////
##  Test
##//////////////////////////////////////////////////////

if __name__ == '__main__':
    features = (
        AlwaysFeatureDetectorList() +
        FunctionFeatureDetectorList(lambda w:w[0],
                           [chr(i) for i in range(ord('a'), ord('z')+1)]) +
        FunctionFeatureDetectorList(lambda w:w[-1],
                           [chr(i) for i in range(ord('a'), ord('z')+1)]) +
        FunctionFeatureDetectorList(lambda w:len(w), range(15)) +
        ValueFeatureDetectorList(("Atlanta's",))
        )

    s = "asdf"
    print features, features.detect(s)
    print [a for a in features.detect(s)]
    print features.detect(s).assignments()
    print features[0], features[12]
    print features[0].detect(s), features[12].detect(s)

