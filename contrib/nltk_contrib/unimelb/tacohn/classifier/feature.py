# Natural Language Toolkit: Feature-Based Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>,
#         Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Basic data classes for building feature-based classifiers.
X{Features} provide a standard way of encoding the information used to
make classification decisions.  This standard encoding allows the same
classifier to be used to solve many different problems.

Features
========
Each feature specifies some aspect of a text that is relevant to
statistical and machine learning approaches to classifying that text.
A text (or other representation of an input instance) is mapped into
feature space, where the attributes of the text relevant to the
classification are extracted and all other information is discarded.
This mapping often reduces the complexity, or dimensionality of the
representation, but may alternatly increase it.  A typical example of
a feature is (which may help classifying the document into the
C{\"sport\"} category):

    - Whether a document contains the word C{\"ball\"}.

Abstractly, features can be thought of as functions mapping from
C{immutable} to values.  For example, the X{feature function}
corresponding to the typical feature given above is::

    f(text)  =  1  if \"ball\" in text
             =  0  otherwise

FIXME --- UP TO HERE

Note that features depend on both the text and the label.  This allows
us to specify which aspects of a text are relevant for making
decisions about which labels.  Feature functions usually have the
form::

    f(ltext)  =  g(ltext.text)   if ltext.label == L
                      0          if ltext.label != L

for some function C{g} and label C{L}.  {g} is sometimes called the
X{context function}. (?)

Abstractly, each feature consists of:

   - A unique X{feature id}, which is used to distinguish the
     feature.  Feature ids are bounded non-negative integers.

   - A X{feature detector}, which encapsulates the feature's
     function.  Feature detectors are implemented using the
     C{FeatureDetectorI} interface.
     
   - A set of possible X{feature value}s that can be produced by the
     feature detector.  In principle, feature detectors can generate
     any immutable value; however, many classifiers require that their
     features have a specific type of value.  The most common sets of
     feature values are:

         - booleans (C{0} and C{1})
         - integers
         - non-negative integers
         - real numbers

Features are not explicitly represented by any object; instead, they
are indirectly represented using feature detectors.

Feature Detector Lists
======================
X{Feature detector lists} provide a way of grouping feature detectors
together.  Abstractly, a feature detector list can be thought of as a
C{list} of feature detectors.  The M{i}th element of this list is the
feature detector for the feature with id M{i}.  

When a feature detector list is applied to a C{LabeledText}, it
returns a X{feature value list}.  Abstractly, a feature value list can
be thought of as a C{list} of feature values.  The M{i}th element of
this list is the feature value for the feature with id M{i}.

Feature detector lists don't just serve to group feature detectors
together; they are also an important tool for efficient feature
detection.  Often, the features used for classification are closely
related to each other.  For example, a document classifier might use
features that examine whether a given word is in a document.  If we
applied each feature detector separately, we would have to scan
through the document once for each word we are interested in.
Instead, we can build a feature detector list that will check for all
relevant words at the same time.

Similarly, feature value lists serve to make feature detection more
efficient.  For many classification tasks, feature value lists are
very sparse; in other words, most of the feature values have some
X{default value} (usually, zero).  Feature value lists provide a
method that can be used to retrieve all of the non-default feature
value assignments.  This can considerably decrease the time that it
takes to process the feature value list.

@warning: We plan to significantly refactor the nltk.classifier
    package for the next release of nltk.

@group Interfaces: FeatureDetectorI, FeatureValueListI,
    FeatureDetectorListI
@sort: FeatureDetectorI, FeatureValueListI, FeatureDetectorListI
@group Feature Detectors: FunctionFeatureDetector
@group Feature Value Lists: ArrayFeatureValueList, EmptyFeatureValueList,
    SimpleFeatureValueList
@group Feature Deteector Lists: AbstractFDList, MergedFDList,
    SimpleFDList, AlwaysOnFDList, TextFunctionFDList,
    BagOfWordsFDList, MultiBagOfWordsFDList, MemoizedFDList
@group Classifiers: AbstractFeatureClassifier
@group Probability Distributions: _AbstractFeatureClassifierProbDist
"""

from nltk_contrib.unimelb.tacohn.classifier import ClassifierI, LabeledText
from nltk.probability import ProbDistI
from nltk.token import Token
from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
import re
import types

# Issues:
#    - Do I want to use FDList or FeatureDetectorList.  E.g., c.f.:
#        * LabeledTextFunctionFDList
#        * LabeledTextFunctionFeatureDetectorList 

##//////////////////////////////////////////////////////
##  Preferred Variable Names
##//////////////////////////////////////////////////////
# Feature id: fid
# Feature value: fval
# Feature detector list: fd_list
# Feature value list: fv_list
# Labeled feature value list: labeled_fv_list or lfv_list
# Assignments: assignments

##//////////////////////////////////////////////////////
##  Feature Values
##//////////////////////////////////////////////////////

# Feature values can be any immutable type.  Typically, feature values
# are booleans, integers, or floats.

##//////////////////////////////////////////////////////
##  Feature Detectors
##//////////////////////////////////////////////////////

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

    Note: Feature detectors are almost never used directly.  Instead,
    C{FeatureDetectorLists} are used, which efficiently encode large
    sets of feature detectors.  C{FeatureDetectorLists} can apply a
    large number of features to a single C{LabeledText} at once.
    """
    def detect(self, text):
        """
        @return: this feature detector's value for the given labeled
            text.
        @rtype: (immutable)
        @param text: the text whose feature value should be detected.
        @type text: (any)
        """
        raise AssertionError()

class FunctionFeatureDetector(FeatureDetectorI):
    """
    A feature detector that uses a given function to find the value of
    a single feature for any C{LabeledText}.  When a
    C{FunctionFeatureDetector} with function M{f} is applied to a
    labeled text M{lt}, it will return M{f(lt)}.
    """
    def __init__(self, function, name=None):
        """
        Construct a new C{FunctionFeatureDetector} from the given
        function.

        @param function: The function that this feature detector is based
            on.  When this feature detector is applied to a labeled
            text M{lt}, it will return M{C{func}(lt)}.
        @type function: C{LabeledText} -> (any)
        @param name: A name for the function used by this feature
            detector.  This name is used in the string representation
            of the feature detector.
        """
        assert _chktype(1, function, types.FunctionType,
                        types.BuiltinFunctionType, types.ClassType)
        assert _chktype(2, name, types.NoneType, types.StringType)
        self._name = name
        self._func = function

    def detect(self, text):
        # Inherit docs from FeatureDetectorI
        return self._func(text)

    def __repr__(self):
        """
        @return: a string representation of this feature detector.
        @rtype: C{string}
        """
        if self._name is None:
            self._name = self._func.__name__+'()'
        return "<FeatureDetector: %s>" % self._name

##//////////////////////////////////////////////////////
##  Feature Value Lists
##//////////////////////////////////////////////////////

class FeatureValueListI:
    """
    A list of the feature values for a particular C{LabeledText}.
    Feature values can be any immutable object.  Typically, feature
    values are booleans (1 or 0); integers; non-negative integers; or
    floats.

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
    assigned the \"default\" value (typically 0).

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
        @raise IndexError: If C{feature_id}<0 or C{feature_id}>=M{N},
            where M{N} is the number of features in this feature
            detector list.
        """
        raise AssertionError()
    
    def default(self):
        """
        @return: the default value for this feature value list.  If a
            feature's value is not returned by C{assignments()},
            then that feature's value is the default value.
        @rtype: (immutable)
        """
        raise AssertionError()

    def __len__(self):
        """
        @return: the number of features whose values are specified by
            this feature value list.  The feature ids for the
            features in this feature value list are the integers M{i},
            where M{0 <= i < C{len(self)}}.
        @rtype: C{int}
        """
        raise AssertionError()

    def assignments(self):
        """
        @return: a list of the feature value assignments for each
            feature in this feature value list whose value is not the
            default value.  These assignments are returned as a
            sequence of C{(feature_id, feature_value)} pairs.  The
            following code demonstrates the typical usage pattern for
            this method::

                for (fid, value) in feature_values.assignments():
                    print 'Feature %d has value %s' % (fid, val)

        @rtype: sequence of (tuple of C{int} and (immutable))
        """
        raise AssertionError()

class ArrayFeatureValueList(FeatureValueListI):
    """
    An array-based implementation of C{FeatureValueListI}.  This
    implementation may be more efficient than
    C{SimpleFeatureValueList} for dense feature value lists.

    @type _values: C{array}
    @ivar _values: A one-dimensional array, containing the value for
        each feature.
    @type _default: (immutable)
    @ivar _default: The default value.
    """
    def __init__(self, values, default=0):
        """
        Build a new C{ArrayFeatureValueList}.

        @type values: C{sequence} of (immutable)
        @param values: The list of the feature values that should be
            encoded by this feature value list.  Element M{i} of
            C{values} is the feature value for the M{i}th feature.
            The length of C{values} is the number of features whose
            value are encoded.
        @type default: (immutable)
        """
        import Numeric
        self._values = Numeric.array(values)
        self._default = default

    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
        assert _chktype(1, feature_id, types.IntType)
        return self._values[feature_id]

    def default(self):
        """
        C{ArrayFeatureValueList} explicitly encodes the value of each
        feature; there will never be a feature whose value is not
        returned by C{assignments()}.  The default value is therefore
        not meaningful.  This method returns zero, since that is the
        standard default value.

        @return: 0
        @rtype: C{int}
        """
        return 0

    def __len__(self):
        # Inherit docs from FeatureValueListI
        return len(self._values)

    def assignments(self):
        # Inherit docs from FeatureValueListI
        return [(i, self._values[i]) for i in range(len(self._values))]

    def __repr__(self):
        """
        @return: a string representation of this feature value
            list, of the form::

                <FeatureValueList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureValueList with %d features>" % len(self)

class EmptyFeatureValueList(FeatureValueListI):
    """
    A feature value list, all of whose features have the default
    value. 
    """
    def __init__(self, len, default=0):
        """
        Construct a new C{EmptyFeatureValueList}
        
        @type len: C{int}
        @param len: The number of features whose values are specified
            by this feature value list.
        @type default: (immutable)
        @param default: The default value for this feature value list.
            This is used as the feature value for every feature.
        """
        assert _chktype(1, len, types.IntType)
        self._len = len
        self._default = default
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
        assert _chktype(1, feature_id, types.IntType)
        return self._default
    def default(self):
        # Inherit docs from FeatureValueListI
        return self._default
    def __len__(self):
        # Inherit docs from FeatureValueListI
        return self._len
    def assignments(self):
        # Inherit docs from FeatureValueListI
        return ()
    def __repr__(self):
        """
        @return: a string representation of this feature value
            list, of the form::

                <FeatureValueList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureValueList with %d features>" % len(self)

class SimpleFeatureValueList(FeatureValueListI):
    """
    A simple list-based implementation of the C{FeatureValueListI}
    interface.  Internally, this implementation stores the feature
    values as a list of assignments; it is therefore an efficient
    encoding for sparse feature value lists.

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
        assert _chktype(1, assignments, [()], ((),))
        assert _chktype(2, len, types.IntType)
        self._assignments = assignments
        self._len = len
        self._default = default

    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
        assert _chktype(1, feature_id, types.IntType)
        if feature_id >= self._len:
            raise IndexError('FeatureValueList index out of range')
        for (id, val) in self._assignments:
            if id == feature_id:
                return val
        return self._default

    def default(self):
        # Inherit docs from FeatureValueListI
        return self._default

    def __len__(self):
        # Inherit docs from FeatureValueListI
        return self._len

    def assignments(self):
        # Inherit docs from FeatureValueListI
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
##  Feature Detector Lists
##//////////////////////////////////////////////////////

class FeatureDetectorListI:
    """
    A list of the C{FeatureDetector}s that correspond to a particular
    set of features.  C{FeatureDetector}s are used to find the value
    of a feature for a given text.

    A feature detector's position in the feature detector list is
    given by its feature's id.  In other words, if M{f} is a feature
    with id M{i}, then M{f}'s detector is the M{i}th element of the
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
    each feature for a given text; the resulting feature values are
    returned as a C{FeatureValueList}.  This can be signifigantly more
    efficient than individually applying each feature detector, since
    many feature detectors are closely related to each other.
    
    Feature detector lists can be combined using the addition
    operator.

    Classes implementing the FeatureDetectorI interface may choose to
    only support certain kinds of labeled texts.  If a method is
    unable to return a correct result because it is given an
    unsupported kind of labeled token, then it should raise a
    NotImplementedError.
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
        @raise IndexError: If C{feature_id}<0 or C{feature_id}>=M{N},
            where M{N} is the number of features in this feature
            detector list.
        """
        raise AssertionError()

    def detect(self, text):
        """
        @return: a feature value list specifying the value of each of
            feature for the given labeled text.
        @rtype: C{FeatureValueListI}
        @param text: the text whose feature values should be detected.
        """
        raise AssertionError()

    def __len__(self):
        """
        @return: the number of features generated by this feature
            detector list.  The feature ids for the features in this
            feature detector list are the integers M{i}, where M{0 <=
            i < C{len(self)}}.
        @rtype: C{int}
        """
        raise AssertionError()

    def __add__(self, other):
        """
        @return: a new feature detector list containing the feature
            detectors from this feature detector list and from the
            other feature detector list.  In this new feature detector
            list:

              - Feature ids M{0...C{len(self)-1}} correspond to
                feature ids M{0...C{len(self)-1}} in C{self}.
              - Feature ids M{C{len(self)}...C{len(self)+len(other)-1}}
                correspond to feature ids M{0...C{len(other)-1}} in
                C{other}.
            
        @rtype: C{FeatureDetectorListI}
        @param other: The feature detector list which should be
            combined with this feature detector list.
        @type other: C{FeatureDetectorListI}
        """
        raise AssertionError()

class AbstractFDList(FeatureDetectorListI):
    """
    An abstraract base class that provides default definitions for
    most C{FeatureDetectorListI} methods.  The only methods that
    subclasses need to implement are C{detect} and C{__len__}.

    This class serves as the base class for most of the feature value
    lists provided by nltk.  It also provides a convenient basis for
    building custom feature detector lists.
    """
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureDetectorListI
        assert _chktype(1, feature_id, types.IntType)
        if feature_id >= len(self) or feature_id < 0:
            raise IndexError('FeatureDetectorList index out of range')
        def f(labeled_text, detect=self.detect, id=feature_id):
            return detect(labeled_text)[id]
        return FunctionFeatureDetector(f, ('f_%d()' % feature_id))

    def __add__(self, other):
        # Inherit docs from FeatureDetectorListI
        # n.b.: Slight circular dependency (since
        # MergedFDList is itself derived from
        # AbstractFDList).
        assert _chktype(1, other, FeatureDetectorListI)
        return MergedFDList(self, other)

    def __repr__(self):
        """
        @return: a string representation of this feature detector
            list, of the form::

                <FeatureDetectorList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureDetectorList with %d features>" % len(self)

    def ranges(self):
        # default implementation
        return [range(len(self))]

    def describe(self, fnum):
        return str(fnum)

class MergedFDList(AbstractFDList):
    """
    A feature detector list that merges the features from two or more
    sublists.

    Note: C{MergedFDList} currently requires that all of
    the sublists generate feature value lists with the same default
    value.

    @type _sub_fd_lists: C{list} of C{FeatureDetectorListI}
    @ivar _sub_fd_lists: The feature detector lists contained by this
        C{MergedFDList}.
    @type _offsets: C{list} of C{int}
    @ivar _offsets: The offset at which each feature detector list
        begins.
    @type _N: C{int}
    @ivar _N: The length of this feature detector list.  This should
        be equal to C{_offsets[-1]+len(_sub_fd_lists[-1])} (unless
        C{len(_offsets)==0}, in which case C{_N=0}).
    """
    def __init__(self, *sub_fd_lists):
        """
        Construct a new feature detector list, containing the features
        from each of the feature detector lists in C{sub_fd_lists}.

        If M{N[i]} is the length of the M{i}th feature detector list,
        then feature id M{j} in C{sub_fd_list[M{i}]} corresponds to
        feature id M{N[0]+N[1]+...+N[i-1]+j} in the merged feature
        detector list.

        @param sub_fd_lists: The feature detector lists to combine.
        @type sub_fd_lists: C{list} of C{FeatureDetectorListI}
        """
        assert _chktype('vararg', sub_fd_lists, (FeatureDetectorListI,))
        self._sub_fd_lists = []
        self._offsets = []
        offset = 0
        for sublist in sub_fd_lists:
            if isinstance(sublist, MergedFDList):
                # Create a single flat merged feature detector list, 
                # rather than a tree of them.
                self._sub_fd_lists += sublist._sub_fd_lists
                self._offsets += [x+offset for x in sublist._offsets]
            else:
                self._sub_fd_lists.append(sublist)
                self._offsets.append(offset)
            offset += len(sublist)

        self._N = offset

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    # This may not be the most efficient method if we're not using
    # feature detector lists that return SimpleFeatureValueLists.  But
    # for now, at least, everything uses SimpleFeatureValueLists.
    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        assignments = []
        default = None
        for i in range(len(self._sub_fd_lists)):
            offset = self._offsets[i]
            fv_list = self._sub_fd_lists[i].detect(text)
            if default != fv_list.default():
                if default is None:
                    default = fv_list.default()
                else:
                    raise ValueError('MergedFDList can '+
                                     'not merge feature value lists '+
                                     'with different default values.')
            assignments += [(fnum+offset, val) for (fnum, val)
                            in fv_list.assignments()]
            
        return SimpleFeatureValueList(assignments, self._N, default)

    def ranges(self):
        rss = []
        for i in range(len(self._sub_fd_lists)):
            offset = self._offsets[i]
            sub_rss = self._sub_fd_lists[i].ranges()
            sub_rss = map(lambda r: [offset + j for j in r], sub_rss)
            rss.extend(sub_rss)
        return rss

    def describe(self, fnum):
        offset = 0
        fd_list_index = 0
        for i in range(len(self._offsets)):
            if fnum >= self._offsets[i]:
                offset = self._offsets[i]
                fd_list_index = i
            else:
                break
        return self._sub_fd_lists[fd_list_index].describe(fnum - offset)

class SimpleFDList(FeatureDetectorListI):
    """
    A feature detector list constructed from a C{list} of
    C{FeatureDetector}s.
    """
    def __init__(self, feature_detectors):
        """
        Construct a new C{SimpleFDList}.

        @param feature_detectors: The C{list} of C{FeatureDetector}s
            that make up the new C{SimpleFeatureDetector}.  The M{i}th
            element of this list is the feature detector for the
            feature with id M{i}.
        @type feature_detectors: C{sequence} of C{FeatureDetectorI}
        """
        assert _chktype(1, feature_detectors, [FeatureDetectorI],
                        (FeatureDetectorI,))
        self._feature_detectors = feature_detectors
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureDetectorListI
        assert _chktype(1, feature_id, types.IntType)
        if feature_id >= len(self) or feature_id < 0:
            raise IndexError('FeatureDetectorList index out of range')
        return self._feature_detectors[feature_id]
    def __add__(self, other):
        # Inherit docs from FeatureDetectorListI
        assert _chktype(1, other, FeatureDetectorListI)
        return MergedFDList(self, other)
    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return len(self._feature_detectors)
    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        values = [fd.detect(text) for fd in self._feature_detectors]
        return ArrayFeatureValueList(values)

class AlwaysOnFDList(AbstractFDList):
    """
    A feature detector list containing a single boolean feature, which
    is always on.
    """
    # Build the feature value once and re-use it, to save
    # time/memory. 
    _FVLIST = SimpleFeatureValueList(((0,1),), 1)
    def __init__(self):
        """
        Construct a new C{AlwaysOnFDList}.
        """
    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return 1
    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        return AlwaysOnFDList._FVLIST

class TextFunctionFDList(AbstractFDList):
    """
    A boolean-valued feature detector list constructed from a function
    over texts, and a set of labels.  This feature detector list
    contains one feature detector for each M{value}, where M{value}
    is a value in the range of the function.  When applied to a
    M{text}, the feature detector corresponding to the value M{value}
    will return:

        - true, if  M{f(text)=value}
        - false, otherwise

    Where M{f} is the function.
    """
    def __init__(self, function, range):
        """
        Construct a new C{TextFunctionFDList}.  This feature
        detector list contains one feature detector for each M{value}
        pair, where M{value} is a value in C{range}.  When applied to
        a text M{text}, the feature detector corresponding to the
        pair M{value} will return:

            - 1, if C{function(M{text})}=M{value}
            - 0, otherwise

        @type function: (immutable) -> (immutable)
        @param function: The function on which this 
            C{TextFunctionFDList} is based.
        @type range: C{list} of (immutable)
        @param range: The range of C{function}.
        """
        assert _chktype(1, function, types.FunctionType,
                        types.BuiltinFunctionType, types.ClassType)
        assert _chktype(2, range, [], ())
        self._func = function

        self._vmap = {}
        self._num_values = 0
        for elt in range:
            if not self._vmap.has_key(elt):
                self._vmap[elt] = self._num_values
                self._num_values += 1

        self._N = self._num_values

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        vnum = self._vmap.get(self._func(text), None)
        if vnum == None:
            return EmptyFeatureValueList(self._N)
        else:
            return SimpleFeatureValueList(((vnum, 1),), self._N)


#### FIXME UP TO HERE ON DOCO

class BagOfWordsFDList(AbstractFDList):
    """
    A boolean-valued feature detector list constructed from a set of
    words and a set of labels.  This feature detector list contains
    one feature detector for each M{word}.  When the feature detector
    corresponding to M{word} is applied to a text M{text}, it will return:

        - 1, if C{M{word} in M{text}}
        - 0, otherwise

    This feature detector assumes that it is applied to texts consisting of
    lists of words.  Words can be any immutable object; they will typically be
    strings.
    """
    def __init__(self, words):
        """
        Construct a new C{BagOfWordsFDList}.  This feature detector
        list contains one feature detector for each M{word}, where
        M{word} is an element of C{words}. When the feature detector
        corresponding to M{word} is applied to a text M{text}, it will
        return:

            - 1, if C{M{word} in M{text}}
            - 0, otherwise

        @type words: C{list} of (immutable)
        @param words: The list of words to look for.
        """
        assert _chktype(1, words, (), [])
        if None in words:
            raise ValueError('TextFunctionFDList can not '+
                             'be used if words contains None')
        
        self._wmap = {}
        self._num_values = 0
        self._words = []
        for word in words:
            if not self._wmap.has_key(word):
                self._wmap[word] = self._num_values
                self._num_values += 1
                self._words.append(word)
        self._N = self._num_values

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        assignments = {}
        for word in text:
            wnum = self._wmap.get(word)
            if wnum is not None:
                assignments[wnum] = 1

        return SimpleFeatureValueList(assignments.items(), self._N)

    def describe(self, index):
        return self._words[index]

class MultiBagOfWordsFDList(BagOfWordsFDList):
    """
    An integer-valued feature detector list constructed from a set of
    words.  This feature detector list contains one feature detector
    for each M{word}.  When the feature detector corresponding to
    M{word} is applied to a labeled text M{text}, it will return:

        - the number of times C{M{word}} appears in C{M{text}}
        - 0, otherwise

    This feature detector assumes that it is applied to texts
    consisting of lists of words.  Words can be any immutable object;
    they will typically be strings.
    """
    # Inherit constructor and __len__ from BagOfWordFDList

    def detect(self, text):
        # Inherit docs from FeatureDetectorListI
        assignments = {}
        for word in labeled_text.text():
            wnum = self._wmap.get(word)
            if wnum is not None:
                assignments[wnum] = assignments.get(wnum, 0) + 1

        return SimpleFeatureValueList(assignments.items(), self._N)

    
class MemoizedFDList(AbstractFDList):
    """
    A feature detector list that always returns the same
    C{FeatureValueList} that a given X{base C{FeatureDetectorList}}
    would; but that pre-computes and re-uses its C{FeatureValueList}s.
    This can signifigantly improve the efficiency of iterative
    training alogrithms, where C{detect} is called repeatedly on the
    same C{texts}.

    When a new C{MemoizedFDList} is constructed, the
    C{FeatureValueList} for each text is precomputed.  When C{detect}
    is called, these precomputed values are returned, when possible.

    Although C{MemoizedFDList} usually improves efficiency, it takes
    space proportional to the number of texts used times the number of
    labels used.  When memory is limited, it may be better not to use
    C{MemoizedFDlist}.
    """
    # TODO - only create the cache as required, maybe?
    def __init__(self, base_fd_list, texts):
        """
        Construct a new C{MemoizedFDList}.  Pre-compute the
        C{FeatureValueList} for each C{text} where C{text} is an
        element of C{texts}.  These pre-computed C{FeatureValueList}s
        will be returned whenever C{detect} is called with the
        corresponding text.

        @param base_fd_list: The base C{FeatureDetectorList}.  This
            C{MemoizedFDList} always returns the same
            C{FeatureValueList} that C{base_fd_list} would.
        @type base_fd_list: C{FeatureDetectorListI}
        @param texts: The list of texts for which C{FeatureValueList}s
            should be pre-computed.
        @type texts: C{sequence} of (immutable)
        """
        assert _chktype(1, base_fd_list, FeatureDetectorListI)
        assert _chktype(2, texts, (), [])
        self._cache = {}
        self._base_fd_list = base_fd_list
        for text in texts:
            self._cache[tuple(text)] = base_fd_list.detect(text)

    def detect(self, text):
        # Inherit docs
        fv_list = self._cache.get(tuple(text), None)
        if fv_list is not None:
            return fv_list
        else:
            return self._base_fd_list.detect(text)

    def __len__(self):
        # Inherit docs
        return len(self._base_fd_list)

#
# New fanstatic filters
#

class FunctionFilter:
    """
    A filter which applies the given M{function} to its argument,
    returning the result. 

    @see: C{FilteredFDList}
    """
    def __init__(self, function):
        """
        Create the filter, wrapping the given C{function}.
        @param function: the function to wrap
        @type  function: C{function} from (any) to (any)
        """
        self._function = function
    def __call__(self, seq):
        """
        Call the function with a single argument.
        @param seq: the argument to the wrapped function
        @type  seq: (any) compatible with the function's input
        @returns:   (any) as per the function's output
        """
        return self._function(seq)

class ArrayFunctionFilter:
    """
    A filter which applies the given M{function} to each item of its
    argument, returning a C{list} containing the return values of each
    call. This can be used, for example, to extract the tag from a
    list of tagged tokens.

    @see: C{FilteredFDList}
    """
    def __init__(self, function):
        """
        Create the filter, wrapping the given C{function}.
        @param function: the function to wrap
        @type  function: C{function} from (any) to (any)
        """
        self._f = function
    def __call__(self, seq):
        """
        Call the function with a single argument.
        @param seq: the argument to the wrapped function
        @type  seq: (sequence) of (any)
        @returns:   (any)
        """
        return map(self._f, seq)

class ArrayIndexFilter:
    """
    Expect to use with index = slice(from, to)
    """
    def __init__(self, index):
        self._index = index
    def __call__(self, seq):
        return seq.__getitem__(self._index)

class CompositeFilter:
    def __init__(self, *filters):
        self._filters = filters
    def __call__(self, seq):
        for filter in self._filters:
            seq = filter(seq)
        return seq

class FilteredFDList(AbstractFDList):
    def __init__(self, filter_function, fd_list, description = None):
        self._filter_function = filter_function
        self._fd_list = fd_list
        self._description = description

    def detect(self, text):
        # Inherit docs
        new_text = self._filter_function(text)
        return self._fd_list.detect(new_text)

    def __len__(self):
        return len(self._fd_list)

    def describe(self, index):
        if self._description:
            return self._description + ' ' + self._fd_list.describe(index)
        else:
            return 'filtered ' + self._fd_list.describe(index)

##//////////////////////////////////////////////////////
##  Abstract Feature Classifier
##//////////////////////////////////////////////////////
class _AbstractFeatureClassifierProbDist(ProbDistI):
    def __init__(self, unlabeled_token, dist_dict):
        assert _chktype(1, unlabeled_token, Token)
        assert _chktype(2, dist_dict, {})
        self._tok = unlabeled_token
        self._dist_dict = dist_dict
    def prob(self, sample):
        if not isinstance(sample, Token):
            return 0
        if sample.loc() != self._tok.loc():
            return 0
        if sample.type().text() != self._tok.type().text():
            return 0
        return self._dist_dict.get(sample.type().label(), 0)
    def max(self):
        max = None
        for label, value in self._dist_dict.items():
            if not max or value > max[0]:
                max = (value, label)
        if max:
            return max[1]
        else:
            return None

class AbstractFeatureClassifier(ClassifierI):
    """
    An abstraract base class that provides default definitions for all
    of the C{ClassifierI} methods.  The only method that subclasses
    need to implement is C{fv_list_likelihood}.  This method returns a
    float indicating the likelihood of a given feature value list.

    Subclasses may override the method C{zero_distribution_list}.
    This method determines what probability distribution should be
    returned if C{fv_list_likelihood} returns zero for every label.
    Its default implementation returns a uniform distribution.

    Subclass constructors should have C{fd_list} and C{labels} as their
    first two arguments; and should use them to call the
    C{AbstractFeatureClassifier} constructor.

    In addition to providing default definitions for the methods
    defined by C{Classifier}, C{AbstractFeatureClassifier} implements
    the method C{fd_list}, which returns the C{FeatureDetectorList}
    used by this classifier.

    @type _fd_list: C{FeatureDetectorListI}
    @ivar _fd_list: The feature detector list defining the features
        that are used by this classifier.
    @type _labels: C{list} of (immutable)
    @ivar _labels: A list of the labels that should be considered by
        this classifier.
    """
    def __init__(self, fd_list, labels):
        """
        Initialize the feature detector list and label list for this
        classifier.  This constructor should be called by subclasses,
        using the statement::

            AbstractFeatureClassifier.__init__(self, fd_list, labels)
            
        @type fd_list: C{FeatureDetectorListI}
        @param fd_list: The feature detector list defining
            the features that are used by the C{Classifier}.
        @type labels: C{list} of (immutable)
        @param labels: A list of the labels that should be considered
            by this C{NBClassifier}.  Typically, labels are C{string}s
            or C{int}s.
        """
        assert _chktype(1, fd_list, FeatureDetectorListI)
        assert _chktype(2, labels, (), [])
        self._fd_list = fd_list
        self._labels = labels
    
    def fv_list_likelihood(self, fv_list, label):
        """
        @rtype: C{float}
        @return: a likelihood estimate for the given feature value
            list.  This estimate should equal M{Z*P(C{fv_list})} for
            some positive normalization constant Z that does not
            depend on the label used to generate C{fv_list}.  The
            estimate must be positive.
        @param fv_list: The feature value list whose likelihood should
            be estimated.
        @type fv_list: C{FeatureValueListI}
        """
        raise AssertionError()

    def zero_distribution_list(self, unlabeled_token):
        """
        Return a list indicating the likelihood that C{unlabeled_token}
        is a member of each category.  This method is called whenever
        C{fv_list_likelihood} returns zero for every text whose text is
        C{unlabled_token.type()}.  Its default behavior is to return a
        uniform distribution; however, it can be overridden to provide a
        different behavior.
        Reasonable alternatives might include:
            - Return zero for each label.
            - Use a modified C{fv_list_likelihood} that allows zeros to
              "cancel out" between different label values.
        
        @return: a list of probabilities.  The M{i}th element of the
            list is the probability that C{unlabeled_text} belongs to
            C{labels()[M{i}]}'s category.
        @rtype: C{sequence} of C{float}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: C{Token}
        """
        assert _chktype(1, unlabeled_token, Token)
        return [1.0/len(self._labels) for l in self._labels]
    
    def distribution_list(self, unlabeled_token):
        # Inherit docs from ClassifierI
        assert _chktype(1, unlabeled_token, Token)
        total_p = 0.0
        text = unlabeled_token.type()

        # Construct a list containing the probability of each label.
        dist_list = []
        fv_list = self._fd_list.detect(text)
        for label in self._labels:
            p = self.fv_list_likelihood(fv_list, label)
            dist_list.append(p)
            total_p += p

        # If p=0 for all samples, return a uniform distribution.
        if total_p == 0:
            return self.zero_distribution_list(unlabeled_token)

        # Normalize the probability fv_list_likelihoods.
        return [p/total_p for p in dist_list]

    def distribution_dictionary(self, unlabeled_token):
        # Inherit docs from ClassifierI
        assert _chktype(1, unlabeled_token, Token)
        dist_dict = {}
        dist_list = self.distribution_list(unlabeled_token)
        for labelnum in range(len(self._labels)):
            dist_dict[self._labels[labelnum]] = dist_list[labelnum]
        return dist_dict

    def distribution(self, unlabeled_token):
        # Inherit docs from ClassifierI
        assert _chktype(1, unlabeled_token, Token)
        dist_dict = self.distribution_dictionary(unlabeled_token)
        return _AbstractFeatureClassifierProbDist(unlabeled_token,
                                                  dist_dict)

    def classify(self, unlabeled_token):
        # Inherit docs from ClassifierI
        assert _chktype(1, unlabeled_token, Token)
        text = unlabeled_token.type()
        
        # (label, likelihood) pair that maximizes likelihood
        max = (None, 0)

        # Find the label that maximizes the non-normalized probability
        # fv_list_likelihoods.
        fv_list = self._fd_list.detect(text)
        for label in self._labels:
            p = self.fv_list_likelihood(fv_list, label)
            if p > max[1]: max = (label, p)

        return Token(LabeledText(text, max[0]), unlabeled_token.loc())

    def prob(self, labeled_token):
        # Inherit docs from ClassifierI
        assert _chktype(1, labeled_token, Token)
        text = labeled_token.type().text()
        label = labeled_token.type().label()
        dd = self.distribution_dictionary(Token(text, labeled_token.loc()))
        return dd.get(label, 0.0)

    def labels(self):
        # Inherit docs from ClassifierI
        return self._labels

    def fd_list(self):
        """
        @rtype: C{FeatureDetectorListI}
        @return: The feature detector list defining the features that
            are used by the C{NBClassifier}.
        """
        return self._fd_list

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this Naive Bayes
            classifier.  
        """
        return ('<Classifier: %d labels, %d features>' %
                (len(self.labels()), len(self.fd_list())))

##//////////////////////////////////////////////////////
## Codecs
##//////////////////////////////////////////////////////

class FeatureValueCodecI:
    """
    Interface for encoder/decoders of feature value lists. These classes
    allow writing and reading of files in common formats used by machine
    learning algorithms and toolkits. A set of labeled tokens is
    serialised by applying a feature detector list to each token's text
    followed by the output of the values in the resultant feature value
    list and the instance's label.

    Similarly, instances decoded from foreign file formats are
    represented as a sequence of (FeatureValueList, label) pairs.
    """

    def __init__(self):
        pass

    def encode(self, stream, fd_list, labeled_tokens, **kwargs):
        """
        Encodes the given tokens into the file stream provided. The
        feature detector list is used on each token to create the feature
        value list, which is then encoded along with the instance's
        label. This method calls C{_encode_fv_lists} which must be
        overriden by subclasses.

        @param stream: file name or open file object. If the former, the
            file will be opened for writing, used for output and then
            closed before returning.
        @type stream: C{file} or C{str}
        @param fd_list: feature detector list. Must be compatible with
            the text used in the labeled tokens.
        @type fd_list: C{FeatureDetectorListI}
        @param labeled_tokens: the labeled tokens to process.
        @type labeled_tokens: C{list} of C{Token}s of C{LabeledText}
        """
        assert _chktype(1, stream, file, types.StringType)
        assert _chktype(2, fd_list, FeatureDetectorListI)
        assert _chktype(3, labeled_tokens, [Token], (Token))
        fv_lists = []
        labels = []
        for labeled_token in labeled_tokens:
            labeled_text = labeled_token.type()
            text = labeled_text.text()
            # assumes that FDLists don't take a labeled text
            #fv_lists.append(fd_list.detect(text))
            fv_lists.append(fd_list.detect(text))
            labels.append(labeled_text.label())
        return self._encode_fv_lists(stream, fv_lists, labels, **kwargs)

    def _encode_fv_lists(self, stream, fv_lists, labels, **kwargs):
        """
        Encodes the feature value lists and their corresponding labels
        into the file stream given. This method must be overidden by
        subclasses. 

        @param stream: file name or open file object. If the former, the
            file will be opened for writing, used for output and then
            closed before returning.
        @type stream: C{file} or C{str}
        @param fv_lists: feature value lists for each instance.
        @type fv_lists: C{list} of C{FeatureValueList}
        @param labels: the labels for each instance.
        @type labels: C{list} of immutable
        """
        assert _chktype(1, stream, file, types.StringType)
        assert _chktype(2, fv_lists, [FeatureValueListI], (FeatureValueListI))
        assert _chktype(3, labels, [], ())
        raise AssertionError()

    def decode(self, stream, **kwargs):
        """
        Decodes the given file, returning a list of instances. 

        @returns: A list of tuples -- one for each instance in the file. Each
            tuple contains a feature value list and a label.
        @returntype: List of (C{FeatureValueList}, String) tuples.
        """
        assert _chktype(1, stream, file, types.StringType)
        raise AssertionError()

    def __repr__(self):
        return '<FeatureValueCodec>'

class ARFFFeatureValueCodec(FeatureValueCodecI):
    """
    Encoder/decoder for the Weka ARFF file format. FIXME
    """

    def __init__(self):
        # inherit doco from FeatureValueCodecI
        FeatureValueCodecI.__init__(self)

    HEADER = '% Automatically generated by nltk.classifier.feature'

    def _encode_fv_lists(self, stream, fv_lists, labels, **kwargs):
        """
        Need some doco here. FIXME
        """
        assert _chktype(1, stream, file, types.StringType)
        assert _chktype(2, fv_lists, [FeatureValueListI], (FeatureValueListI))
        assert _chktype(3, labels, [], ())
        assert len(fv_lists) > 0
        assert len(fv_lists) == len(labels)

        name = kwargs.get('name', 'untitled')
        attributes = kwargs.get('attributes')
        attribute_values = kwargs.get('attribute_values')
        # chk these types...

        num_attributes = len(fv_lists[0])
        num_instances = len(fv_lists)

        # find the attribute names - allocate defaults if unspecified
        if attributes:
            assert len(attributes) == num_attributes + 1
        else:
            attributes = [ 'attribute_%d' % i for i in range(num_attributes) ]
            # the last attribute is the class or label
            attributes.append('class')

        # find the attribute values - allocate defaults if unspecified
        if attribute_values:
            assert len(attribute_values) == num_attributes + 1
        else:
            # defaults are a little crazy; basically collate the
            # set of values observed for each feature
            attribute_values = []
            for ai in range(num_attributes):
                attribute_values.append({})
                
            # each attribute value dictionary will hold a key
            # for each feature value
            for fv_list in fv_lists:
                for fi in range(num_attributes):
                    val = fv_list[fi]
                    attribute_values[fi].setdefault(val, 1)

            # see if we can be a bit intelligent about processing these
            # if they're all strings, then ok we'll just use the set
            # however, if they're numeric and there are more than two
            # values, use a real attribute value
            for ai in range(num_attributes):
                avs = attribute_values[ai].keys()
                avs.sort()
                if len(avs) > 2:
                    numbers = 0
                    for av in avs:
                        try:
                            float(av)
                            numbers += 1
                        except ValueError: pass
                        except TypeError: pass
                    if numbers == len(avs):
                        avs = 'real'
                attribute_values[ai] = avs

            # have to coerce the labels too
            label_values = {}
            for label in labels:
                label_values.setdefault(label, 0)
                label_values[label] += 1
            label_values = label_values.keys()
            label_values.sort()
            attribute_values.append(label_values)

        # start writing the file - this test ensures that
        # file names are accepted as well as open files.
        out = stream
        try:
            print >>out, self.HEADER
        except AttributeError:
            out = open(stream, 'w')
            print >>out, self.HEADER

        # name of the data set
        print >>out
        print >>out, '@relation', name
        print >>out

        print >>out, '%% %d instances, %d attributes' % (num_instances,
                                                         num_attributes)

        # attribute description for each attribute
        for name, value in zip(attributes, attribute_values):
            print >>out, '@attribute', name, 
            if value == 'real':
                print >>out, value
            else:
                # print the set of values
                print >>out, '{',
                comma = False
                for option in value:
                    if comma:
                        out.write(', ')
                    comma = True
                    print >>out, self._escape(str(option)),
                print >>out, '}'

        # the data part
        print >>out
        print >>out, '@data'

        for fv_list, label in zip(fv_lists, labels):
            comma = False
            for fi in range(num_attributes):
                if comma:
                    out.write(',')
                comma = True
                out.write(self._escape(str(fv_list[fi])))
            if comma:
                out.write(',')
            print >>out, self._escape(str(label))

        # if we opened the file, we should close it too
        if stream != out:
            out.close()

        return

    def _escape(self, text):
        if re.search(r'[?,{}\'"%\s]', text):
            if re.search(r'"', text):
                text = re.sub(r'"', r'\"', text)
            return '"%s"' % text
        else:
            return text

    def decode(self, stream, **kwargs):
        # accept order of attributes - including which is the label
        # accept default values for instances; 0 if numeric
        relation = None
        attribute_names = []
        attribute_values = []
        instances = []
        header = True
        line = ''
        line_no = 0

        # open the file if it's a string
        input = stream
        try:
            line = input.readline()
            line_no += 1
        except AttributeError:
            input = open(stream, 'r')
            line = input.readline()
            line_no += 1

        relation_re =       re.compile(r'@relation\s+(.*)', re.I)
        attribute_re =      re.compile(r'@attribute\s+([^\s]+)\s+(.*)', re.I)
        sub_attribute_re =  re.compile(r'[^{},\s]+')
        data_re =           re.compile(r'@data', re.I)
        instance_re =       re.compile(r'[^,\s]+')
        real_re =           re.compile(r'real', re.I)

        # process line by line
        while line:
            line = line.strip()
            if line and not line.startswith('%'):
                if header:
                    attr_m = attribute_re.match(line)
                    data_m = data_re.match(line)
                    rel_m = relation_re.match(line)
                    if attr_m:
                        name = attr_m.group(1)
                        attribute_names.append(name)
                        attr = attr_m.group(2)
                        attr.strip()
                        if real_re.match(attr):
                            attribute_values.append('real')
                        else:
                            # are there are other types (range, integer...)?
                            attribute_values.append(
                                sub_attribute_re.findall(attr))
                    elif rel_m:
                        relation = rel_m.group(1)
                    elif data_m:
                        header = False
                    else:
                        print >>sys.stderr, 'Syntax error: line', line_no
                else:
                    values = instance_re.findall(line)
                    values_typed = []
                    for attr, value in zip(attribute_values, values):
                        if isinstance(attr, str) \
                           and real_re.match(attr):
                            values_typed.append(float(value))
                        else:
                            values_typed.append(value)
                    instances.append(values_typed)
            
            line = input.readline()
            line_no += 1
            
        # close the file if we opened it
        if input != stream:
            input.close()

        # massage the instances into feature value lists etc
        attributes = zip(attribute_names[:-1], attribute_values[:-1])
        fv_lists = []
        instance_labels = []
        for instance in instances:
            # ArrayFVL doesn't cope with text strings
            #fv_list = ArrayFeatureValueList(instance[:-1])
            fv_list = SimpleFeatureValueList([(i, instance[i]) for i in
                    range(len(attributes))], len(attributes))
            label = instance[-1]
            fv_lists.append(fv_list)
            instance_labels.append(label)
        labels = attribute_values[-1]

        return fv_lists, instance_labels, relation, attributes, labels

    def __repr__(self):
        return '<ARFFFeatureValueCodec>'

##//////////////////////////////////////////////////////
##  Test
##//////////////////////////////////////////////////////

def _test_codecs():
    words = [ 'hello', 'what', 'a', 'wonderful', 'day', 'and', 'how', 
              'lovely', 'is', 'it', 'to', 'be', 'alive' ]
    labels = [ 'funny', 'so-so', 'dry' ]
    file = 'codec_test.arff'
    N_i = 10
    N_w = 10

    fdl = BagOfWordsFDList(words)

    import random
    instances = []
    for i in range(N_i):
        ws = []
        for i in range(N_w):
            ws.append(random.choice(words))
        instances.append(Token(LabeledText(ws, random.choice(labels))))

    codec = ARFFFeatureValueCodec()
    codec.encode(file, fdl, instances, name='random-words')

    stuff = codec.decode(file)
    fvls, ils, rl, attrs, lbls = stuff
    
    print 'relation', rl, 'attributes', attrs, 'labels', lbls

    def fvl2str(fvl):
        return ', '.join([str(fv) for fv in fvl])

    for i in range(N_i):
        print 'instance', i
        print 'input to encoding   ',
        print fvl2str(fdl.detect(instances[i].type().text())),
        print instances[i].type().label()
        print 'output from decoding', fvl2str(fvls[i]), ils[i]

def _test_filters():
    from nltk.corpus import brown
    input = brown.tokenize('cp04')[:14] # the first sentence

    just_tags = ArrayFunctionFilter(lambda tk: tk.type().tag())
    just_base = ArrayFunctionFilter(lambda tk: tk.type().base())
    first_two = ArrayIndexFilter(slice(2))
    two_tags = CompositeFilter(first_two, just_tags)
    two_words = CompositeFilter(first_two, just_base)
    def csort(tks): a = tks[:]; a.sort(); return a
    sort_things = FunctionFilter(csort)
    sort_word = CompositeFilter(just_base, sort_things)

    print 'input:', input
    print 'tags: ', just_tags(input)
    print 'words:', just_base(input)
    print 'pair: ', first_two(input)
    print 'pairt: ', two_tags(input)
    print 'pairw: ', two_words(input)
    print 'sortw: ', sort_word(input)
    print

    bag_of_words = BagOfWordsFDList(just_base(input))
    filtered_bag_of_words = FilteredFDList(just_base, bag_of_words)
    sorted_bag_of_words = FilteredFDList(sort_word, bag_of_words)
    print 'bow: ', bag_of_words.detect(just_base(input)).assignments()
    print 'fbow:', filtered_bag_of_words.detect(input).assignments()
    print 'sbow:', sorted_bag_of_words.detect(input).assignments()

def _test_fd_lists():
    labels = 'A B C D E F G'.split()
    features = (
        AlwaysOnFDList() +
        TextFunctionFDList(lambda w:w[0],
                           [chr(i) for i in range(ord('a'), ord('z')+1)]) +
        TextFunctionFDList(lambda w:w[-1],
                           [chr(i) for i in range(ord('a'), ord('z')+1)]) +
        TextFunctionFDList(lambda w:len(w), range(15))
        )
    
    s = "ASDF"
    print features, features.detect(s)
    print [a for a in features.detect(s)]
    print features.detect(s).assignments()
    print features[0], features[12]
    print features[0].detect(s), features[12].detect(s)

if __name__ == '__main__':
    #_test_fd_lists()
    _test_filters()
    #_test_codecs()

