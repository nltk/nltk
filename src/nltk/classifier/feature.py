# Natural Language Toolkit: Feature-Based Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Basic data classes for building feature-based classifiers.
X{features} provide a standard way of encoding the information used to
make classification decisions.  This standard encoding allows the same
classifier to be used to solve many different problems.

Features
========
Each feature specifies some aspect of a C{LabeledText} that is
relevant to deciding how likely that C{LabeledText} is to occur.
These features can then be used to examine how likely different labels
are for a given text.  A typical example of a feature is:

    - Whether a document contains the word C{\"ball\"} and has
      the label C{\"sports\"}.

Abstractly, features can be thought of as functions mapping from
C{LabeledText}s to values.  For example, the X{feature function}
corresponding to the typical feature given above is::

    f(ltext)  =  1  if ((\"ball\" in ltext.text) and
                        (ltext.label == \"sports\"))
                       
              =  0  otherwise

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
value assignments.  This can decrease the time that it takes to
process the feature value list considerably.

Labeled Feature Value Lists
===========================
Often, it is useful to associate a label with a feature value list.
The C{LabeledFeatureValueList} class can be used for this purpose.
Typically, each C{LabeledFeatureValueList} corresponds to a text,
where the labels are identical, and the feature value list is obtained
by applying some feature detector list to the text.
"""

# Issues:
#    - Do I want to use FDList or FeatureDetectorList.  E.g., c.f.:
#        * LabeledTextFunctionFDList
#        * LabeledTextFunctionFeatureDetectorList 

##//////////////////////////////////////////////////////
##  Preferred Variable Names
##//////////////////////////////////////////////////////
# Feature id: fid
# Feature value: fval
# Feature detector list: fdlist
# Feature value list: fvlist
# Labeled feature value list: labeled_fvlist or lfvlist
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
    def detect(self, labeled_text):
        """
        @return: this feature detector's value for the given labeled
            text.
        @rtype: (immutable)
        @param labeled_text: the labeled text whose feature value
            should be detected.
        @type labeled_text: C{LabeledText}
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
        self._name = name
        self._func = function

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorI
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
        self._values = array(values)
        self._default = default

    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
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
        self._len = len
        self._default = default
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
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
        self._assignments = assignments
        self._len = len
        self._default = default

    def __getitem__(self, feature_id):
        # Inherit docs from FeatureValueListI
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
    of a feature for a given C{LabeledText}.

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

    def detect(self, labeled_text):
        """
        @return: a feature value list specifying the value of each of
            feature for the given labeled text.
        @rtype: C{FeatureValueListI}
        @param labeled_text: the labeled text whose feature values
            should be detected.
        @type labeled_text: C{LabeledText}
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
    Provide default definitions for most C{FeatureDetectorListI}
    methods.  The only methods that subclasses need to implement are 
    C{detect} and C{__len__}.

    This class serves as the base class for most of the feature value
    lists provided by nltk.  It also provides a convenient basis for
    building custom feature detector lists.
    """
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureDetectorListI
        if feature_id >= len(self) or feature_id < 0:
            raise IndexError('FeatureDetectorList index out of range')
        def f(labeled_text, detect=self.detect, id=feature_id):
            return id in detect(labeled_text)
        return FunctionFeatureDetector(f, ('f_%d()' % feature_id))

    def __add__(self, other):
        # Inherit docs from FeatureDetectorListI
        # n.b.: Slight circular dependency (since
        # MergedFDList is itself derived from
        # AbstractFDList).
        return MergedFDList(self, other)

    def __repr__(self):
        """
        @return: a string representation of this feature detector
            list, of the form::

                <FeatureDetectorList with 72 features>
            
        @rtype: C{string}
        """
        return "<FeatureDetectorList with %d features>" % len(self)

class MergedFDList(AbstractFDList):
    """
    A feature detector list that merges the features from two or more
    sublists.

    Note: C{MergedFDList} currently requires that all of
    the sublists generate feature value lists with the same default
    value.

    @type _sub_fdlists: C{list} of C{FeatureDetectorListI}
    @ivar _sub_fdlists: The feature detector lists contained by this
        C{MergedFDList}.
    @type _offsets: C{list} of C{int}
    @ivar _offsets: The offset at which each feature detector list
        begins.
    @type _N: C{int}
    @ivar _N: The length of this feature detector list.  This should
        be equal to C{_offsets[-1]+len(_sub_fdlists[-1])} (unless
        C{len(_offsets)==0}, in which case C{_N=0}).
    """
    def __init__(self, *sub_fdlists):
        """
        Construct a new feature detector list, containing the features
        from each of the feature detector lists in C{sub_fdlists}.

        If M{N[i]} is the length of the M{i}th feature detector list,
        then feature id M{j} in C{sub_fdlist[M{i}]} corresponds to
        feature id M{N[0]+N[1]+...+N[i-1]+j} in the merged feature
        detector list.

        @param sub_fdlists: The feature detector lists to combine.
        @type sub_fdlists: C{list} of C{FeatureDetectorListI}
        """
        self._sub_fdlists = []
        self._offsets = []
        offset = 0
        for sublist in sub_fdlists:
            if isinstance(sublist, MergedFDList):
                # Create a single flat merged feature detector list, 
                # rather than a tree of them.
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
    # feature detector lists that return SimpleFeatureValueLists.  But
    # for now, at least, everything uses SimpleFeatureValueLists.
    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        assignments = []
        default = None
        for i in range(len(self._sub_fdlists)):
            offset = self._offsets[i]
            fvlist = self._sub_fdlists[i].detect(labeled_text)
            if default != fvlist.default():
                if default is None:
                    default = fvlist.default()
                else:
                    raise ValueError('MergedFDList can '+
                                     'not merge feature value lists '+
                                     'with different default values.')
            assignments += [(fnum+offset, val) for (fnum, val)
                            in fvlist.assignments()]
            
        return SimpleFeatureValueList(assignments, self._N, default)

class SimpleFDList:
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
        self._feature_detectors = feature_detectors
    def __getitem__(self, feature_id):
        # Inherit docs from FeatureDetectorListI
        if feature_id >= len(self) or feature_id < 0:
            raise IndexError('FeatureDetectorList index out of range')
        return self._feature_detectors[feature_id]
    def __add__(self, other):
        # Inherit docs from FeatureDetectorListI
        return MergedFDList(self, other)
    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return len(self._feature_detectors)
    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        values = [fd.detect(labeled_text)
                  for fd in self._feature_detectors]
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
    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        return AlwaysOnFDList._FVLIST

class LabeledTextFunctionFDList(AbstractFDList):
    """
    A boolean-valued feature detector list constructed from a function
    over labeled texts.  This feature detector list contains one
    feature detector for each value in the range of the function.
    Each feature will return true iff the function returns the
    corresponding value, when applied to a C{LabeledText}.

    @type _map: C{dictionary} from (immutable) to C{int}
    @ivar _map: A dictionary mapping each value in the function's
        range to the feature id of the feature corresponding to that
        value. 
    """
    def __init__(self, function, range):
        """
        Construct a new C{LabeledTextFunctionFDList}.  This 
        feature detector list contains one feature detector for each
        value in C{range}.  When applied to a labeled text M{ltext},
        the feature detector corresponding to the function value M{v}
        will return:

            - 1, if C{function(M{ltext})==M{v}}
            - 0, otherwise

        @type function: C{LabeledText} -> (immutable)
        @param function: The function on which this 
            C{LabeledTextFunctionFDList} is based.
        @type range: C{list} of (immutable)
        @param range: The range of C{function}.  
        """
        self._func = function

        self._map = {}
        self._N = 0
        for elt in range:
            if not self._map.has_key(elt):
                self._map[elt] = self._N
                self._N += 1

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        fid = self._map.get(self._func(labeled_text), None)
        if fid is None:
            return EmptyFeatureValueList(self._N)
        else:
            return SimpleFeatureValueList(((fid, 1),), self._N)
            

class TextFunctionFDList(AbstractFDList):
    """
    A boolean-valued feature detector list constructed from a function
    over texts, and a set of labels.  This feature detector list
    contains one feature detector for each M{(v, l)} pair, where M{v}
    is a value in the range of the function; and M{l} is a label.
    When applied to a labeled text M{ltext}, the feature detector
    corresponding to the pair M{(v, l)} will return:

        - true, if M{ltext.label=l} and M{f(ltext.text)=v}
        - false, otherwise

    Where M{f} is the C{TextFunctionFDList}'s function.
    """
    #
    # The feature id for a pair (v,l) is:
    #    _vmap[v] + _lmap[l]*_num_values
    #
    def __init__(self, function, range, labels):
        """
        Construct a new C{TextFunctionFDList}.  This feature
        detector list contains one feature detector for each M{(v, l)}
        pair, where M{v} is a value in C{range}, and M{l} is an
        element of C{labels}.  When applied to a labeled text
        M{ltext}, the feature detector corresponding to the pair M{(v,
        l)} will return:

            - 1, if C{function(M{ltext}.text())=M{v} and
                      M{ltext}.label()==M{l}}
            - 0, otherwise

        @type function: (immutable) -> (immutable)
        @param function: The function on which this 
            C{TextFunctionFDList} is based.
        @type range: C{list} of (immutable)
        @param range: The range of C{function}.
        @type labels: C{list} of (immutable)
        @param labels: The set of labels used by this
            C{TextFunctionFDList}. 
        """
        self._func = function
        self._labels = labels

        self._vmap = {}
        self._num_values = 0
        for elt in range:
            if not self._vmap.has_key(elt):
                self._vmap[elt] = self._num_values
                self._num_values += 1

        self._lmap = {}
        self._num_labels = 0
        for elt in labels:
            if not self._lmap.has_key(elt):
                self._lmap[elt] = self._num_labels
                self._num_labels += 1

        self._N = self._num_values * self._num_labels

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        lnum = self._lmap.get(labeled_text.label(), None)
        vnum = self._vmap.get(self._func(labeled_text.text()), None)
        if (lnum == None) or (vnum == None):
            return EmptyFeatureValueList(self._N)
        else:
            fid = vnum + lnum*self._num_values
            return SimpleFeatureValueList(((fid, 1),), self._N)

class BagOfWordsFDList(AbstractFDList):
    """
    A boolean-valued feature detector list constructed from a set of
    words and a set of labels.  This feature detector list contains
    one feature detector for each M{(word,label)} pair.  When the
    feature detector corresponding to M{(word, label)} is applied to a
    labeled text M{ltext}, it will return:

        - 1, if C{M{word} in M{ltext}.text() and
                  M{ltext}.label()==M{label}}
        - 0, otherwise

    This feature detector assumes that it is applied to texts
    consisting of lists of words.  Words can be any immutable object;
    they will typically be strings.
    """
    # The feature id for a pair (w, l) is:
    #    _wmap[w] + _lmap[l]*_num_words
    def __init__(self, words, labels):
        """
        Construct a new C{BagOfWordsFDList}.  This feature

        detector list contains one feature detector for each
        M{(word,label)} pair, where M{word} is an element of C{words},
        and M{label} is an element of C{labels}.  When the feature
        detector corresponding to M{(word, label)} is applied to a
        labeled text M{ltext}, it will return:

            - 1, if C{M{word} in M{ltext}.text() and
                      M{ltext}.label()==M{label}}
            - 0, otherwise

        @type words: C{list} of (immutable)
        @param words: The list of words to look for.
        @type labels: C{list} of (immutable)
        @param labels: The set of labels used by this
            C{TextFunctionFDList}. 
        """
        if None in words:
            raise ValueError('TextFunctionFDList can not '+
                             'be used if words contains None')
        if None in labels:
            raise ValueError('TextFunctionFDList can not '+
                             'be used if labels contains None')
        
        self._wmap = {}
        self._num_words = 0
        for word in words:
            if not self._wmap.has_key(word):
                self._wmap[word] = self._num_words
                self._num_words += 1

        self._lmap = {}
        self._num_labels = 0
        for label in labels:
            if not self._lmap.has_key(label):
                self._lmap[label] = self._num_labels
                self._num_labels += 1

        self._N = self._num_values * self._num_labels

    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return self._N

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        lnum = self._lmap.get(labeled_text.label(), None)
        if lnum is None: return EmptyFeatureValueList()
        offset = lnum*self._num_values

        assignments = []
        for word in labeled_text.text():
            wnum = self._wmap.get(word)
            if wnum is not None:
                assignments.append((wnum+offset, 1))

        return SimpleFeatureValueList(assignments, self._N)

##//////////////////////////////////////////////////////
##  Labeled FeatureValueList
##//////////////////////////////////////////////////////

class LabeledFeatureValueList:
    """
    The label and feature values that correspond to a C{LabeledText}.
    This class encapsulates all of the information about a
    C{LabeledText} that a feature-based classifier can use.
    """
    def __init__(self, fvlist, label):
        """
        Construct a new C{LabeledFeatureValueList}.
        C{LabeledFeatureValueList}s are typically constructed from
        C{LabeledText}s.  For example, the following code constructs a
        new labeled feature value list for C{labeled_text}.  It uses
        C{feature_detector_list} to produce the feature value list::

            >>> fvlist = feature_detector_list.detect(labeled_text)
            >>> label = labeled_text.label()
            >>> lfvlist = LabeledFeatureValueList(fvlist, label)
        
        @param fvlist: The feature value list
        @type fvlist: C{FeatureValueList}
        @param label: The label
        @type label: C{string}
        """
        self._fvlist = fvlist
        self._label = label
        
    def feature_values(self):
        """
        @return: this C{LabeledFeatureValueList}'s feature value list.
        @rtype: C{FeatureValueList}
        """
        return self._fvlist
    
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
        return '%r/%r' % (self._fvlist, self._label) 

##//////////////////////////////////////////////////////
##  Feature Selection
##//////////////////////////////////////////////////////

##//////////////////////////////////////////////////////
##  Test
##//////////////////////////////////////////////////////

if __name__ == '__main__':
    labels = 'A B C D E F G'.split()
    features = (
        AlwaysOnFDList() +
        TextFunctionFDList(lambda w:w[0],
                           [chr(i) for i in range(ord('a'), ord('z')+1)],
                           labels) +
        TextFunctionFDList(lambda w:w[-1],
                           [chr(i) for i in range(ord('a'), ord('z')+1)],
                           labels) +
        TextFunctionFDList(lambda w:len(w), range(15), labels)
        )

    s = LabeledText("asdf", "A")
    print features, features.detect(s)
    print [a for a in features.detect(s)]
    print features.detect(s).assignments()
    print features[0], features[12]
    print features[0].detect(s), features[12].detect(s)

