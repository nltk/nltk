# Natural Language Toolkit: Feature Selection
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces used to select which features are relevant for
a given classification task.

  - C{FeatureSelectorI} defines a standard interface for selecting
    which features from a given C{FeatureDetectorList} are relevant to
    a classification problem.

  - C{SelectedFDList} provides feature selectors with a convenient
    means of building C{FeatureDetectorList}s containing the feature
    detectors for the relevant features.

This module also defines classes implementing the C{FeatureSelectorI}
interface.
"""

from nltk.classifier import *
from nltk.classifier.feature import *

class FeatureSelectorI:
    """
    A processing interface for selecting which features are relevant
    to a given classification problem.  Feature selectors must
    implement a single method, C{select}.  This method takes a
    C{FeatureDetectorList}, and returns a new C{FeatureDetectorList}
    that implements the features from the given C{FeatureDetectorList}
    that are relevant to the classificaiton task.
    """
    def select(self, fd_list):
        """
        Decide which features are relevant for classification; and
        return a new C{FeatureDetectorList} implementing those
        features.  All features must be selected from C{fd_list}.  In
        particular, if M{new_fd_list} is the C{FeatureDetectorList}
        returned by C{select}, then the following must be true for all
        labeled texts M{lt} and feature ids M{id}, and for some
        function M{f()}::

            new_fd_list[id].detect(lt) = fd_list[f(id)].detect(lt)
        
        @return: a C{FeatureDetectorList} that implements the features
            from C{fd_list} that are relevant.
        @rtype: C{FeatureDetectorListI}
        @param fd_list: The C{FeatureDetectorList} from which features
            detectors should be chosen.
        @type fd_list: C{FeatureDetectorListI}
        """
        raise AssertionError()

class SelectedFDList(AbstractFDList):
    """
    A feature detector list that implements a subset of the features
    defined by a X{base C{FeatureDetectorList}}.  C{SelectedFDList} is
    used by C{FeatureSelector}s to select the set of features that are
    relevant for a given classification task.
    """
    def __init__(self, sub_fd_list, selected_ids):
        """
        Construct a new C{SelectedFDList}.  This feature detector list
        implements the features from C{sub_fd_list} that are indicated
        by C{selected_ids}.  In particular, the following is true for
        all feature ids M{0<=id<len(self)} and C{LabeledText}s M{lt}::

          self[id].detect(lt) = sub_fd_list[selected_ids.index(id)].detect(lt)

        @type sub_fd_list: C{FeatureDetectorListI}
        @param sub_fd_list: The C{FeatureDetectorList} that this
            C{SelectedFDList} is based on.
        @type selected_ids: C{sequence} of C{int}
        @param selected_ids: The feature ids for the feature detectors
            that should be included in the C{SelectedFDList}.  This
            list should not contain duplicate feature ids.
        """
        N = 0
        idmap = {}
        for id in selected_ids:
            if not idmap.has_key(id):
                idmap[id] = N
                N += 1
                
        self._N = N
        self._idmap = idmap
        self._sub_fd_list = sub_fd_list
            
    def __len__(self):
        # Inherit docs from AbstractFDList
        return self._N

    def detect(self, labeled_text):
        # Inherit docs from AbstractFDList
        fv_list = self._sub_fd_list.detect(labeled_text)
        assignments = [(self._idmap.get(id), val) for (id, val)
                       in fv_list.assignments()
                       if self._idmap.has_key(id)]
        return SimpleFeatureValueList(assignments, self._N,
                                      fv_list.default())

class AttestedFeatureSelector(FeatureSelectorI):
    """
    A feature selector that selects all features that could possibly
    apply to any of the texts in a given training set.  A feature can
    apply to a text M{t} if the feature value for C{LabeledText(l,t)}
    is not the default value for any label M{l}.
    """
    def __init__(self, training_data, **kwargs):
        """
        Construct a new C{AttestedFeatureSelector}.  Given a
        C{FeatureDetectorList} M{fd_list}, this feature selector will
        select any feature with id M{id} such that::

            fd_list[id].detect(LabeledText(l, t)) != (default)

        For any text M{t} from training_data, and any label M{l}.
        
        @param kwargs: Keyword arguments.
          - C{labels}: The set of labels that should be considered
            by this C{AttestedFeatureSelector} to decide whether a
            feature can apply to a text.  If none is given, then the
            set of all labels attested in the training data will be
            used instead.  (type=C{list} of (immutable)).             
          - C{min_count}: The minimum number of C{LabeledText}s to 
            which a feature must apply, in order to be included in the
            feature value list.  Default=1.  (type=C{int})
        """
        self._training_data = training_data
        
        # Process the keyword arguments.
        self._min_count = 1
        self._labels = None
        for (key, val) in kwargs.items():
            if key == 'min_count':
                self._min_count = val
            elif key == 'labels':
                self._labels = val
            else:
                raise TypeError('Unknown keyword arg %s' % key)
            
        # Find the labels, if necessary.
        if self._labels is None:
            self._labels = find_labels(training_data)

    def select(self, fd_list):
        # Count the number of times each feature is attested.
        attested = {}
        for labeled_token in self._training_data:
            text = labeled_token.type().text()
            for label in self._labels:
                fv_list = fd_list.detect(LabeledText(text, label))
                default = fv_list.default()
                for (id, val) in fv_list.assignments():
                    if val != default:
                        attested[id] = attested.get(id, 0) + 1

        # Construct the list of selected ids.  This is easy if
        # min_count = 1.  Otherwise, loop through the entries of
        # attested. 
        if self._min_count == 1:
            selected_ids = attested.keys()
        else:
            selected_ids = []
            for (id, count) in attested.items():
                if count >= self._min_count:
                    selected_ids.append(id)

        # Return the selected feature detector list.
        return SelectedFDList(fd_list, selected_ids)
