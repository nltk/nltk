# Natural Language Toolkit: Interface to scikit-learn classifiers
#
# Author: Lars Buitinck <L.J.Buitinck@uva.nl>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.classify.api import ClassifierI
from nltk.probability import DictionaryProbDist

import numpy as np


class SklearnClassifier(ClassifierI):
    """Wrapper for scikit-learn classifiers."""

    def __init__(self, estimator, dtype=float, sparse=True):
        """
        :param estimator: scikit-learn classifier object.

        :dtype: data type used when building feature array. Use e.g. bool
            when all features are binary.

        :sparse: Whether to use sparse matrices. Note that the estimator
            must support these; not all scikit-learn classifiers do.
        """
        self._clf = estimator
        self._dtype = dtype
        self._sparse = sparse

    def batch_classify(self, featuresets):
        X = self._featuresets_to_array(featuresets)
        y = self._clf.predict(X)
        return [self._index_label[int(yi)] for yi in y]

    def batch_prob_classify(self, featuresets):
        X = self._featuresets_to_array(featuresets)
        y_proba = self._clf.predict_proba(X)
        return [self._make_probdist(y_proba[i]) for i in xrange(len(y_proba))]

    def labels(self):
        return self._label_index.keys()

    def train(self, labeled_featuresets):
        self._feature_index = {}
        self._index_label = []
        self._label_index = {}

        for fs, label in labeled_featuresets:
            for f in fs.iterkeys():
                if f not in self._feature_index:
                    self._feature_index[f] = len(self._feature_index)
            if label not in self._label_index:
                self._index_label.append(label)
                self._label_index[label] = len(self._label_index)

        featuresets, labels = zip(*labeled_featuresets)
        #featuresets = [fs for fs, _ in labeled_featuresets]
        X = self._featuresets_to_array(featuresets)
        y = np.array([self._label_index[l] for l in labels])

        self._clf.fit(X, y)

        return self

    def _featuresets_to_array(self, featuresets):
        if self._sparse:
            from scipy.sparse import lil_matrix
            zeros = lil_matrix
        else:
            zeros = np.zeros

        X = zeros((len(featuresets), len(self._feature_index)),
                  dtype=self._dtype)

        for i, fs in enumerate(featuresets):
            for f, v in fs.iteritems():
                try:
                    X[i, self._feature_index[f]] = self._dtype(v)
                except KeyError:    # feature not seen in training
                    pass

        return X

    def _make_probdist(self, y_proba):
        return DictionaryProbDist(dict((self._index_label[i], p)
                                       for i, p in enumerate(y_proba)))


if __name__ == "__main__":
    from nltk.classify.util import names_demo, binary_names_demo_features
    from sklearn.naive_bayes import BernoulliNB
    from sklearn.svm.sparse import LinearSVC

    print("scikit-learn Naive Bayes:")
    names_demo(SklearnClassifier(BernoulliNB(), dtype=bool).train,
               features=binary_names_demo_features)
    print("scikit-learn linear SVM:")
    names_demo(SklearnClassifier(LinearSVC(), dtype=bool).train,
               features=binary_names_demo_features)
