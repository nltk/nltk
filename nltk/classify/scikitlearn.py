# Natural Language Toolkit: Interface to scikit-learn classifiers
#
# Author: Lars Buitinck <L.J.Buitinck@uva.nl>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
scikit-learn (http://scikit-learn.org) is a machine learning library for
Python, supporting most of the basic classification algorithms, including SVMs,
Naive Bayes, logistic regression and decision trees.

This package implement a wrapper around scikit-learn classifiers. To use this
wrapper, construct a scikit-learn classifier, then use that to construct a
SklearnClassifier. E.g., to wrap a linear SVM classifier with default settings,
do

>>> from sklearn.svm.sparse import LinearSVC
>>> from nltk.classify.scikitlearn import SklearnClassifier
>>> classif = SklearnClassifier(LinearSVC())

The scikit-learn classifier may be arbitrarily complex. E.g., the following
constructs and wraps a Naive Bayes estimator with tf-idf weighting and
chi-square feature selection:

>>> from sklearn.feature_extraction.text import TfidfTransformer
>>> from sklearn.feature_selection import SelectKBest, chi2
>>> from sklearn.naive_bayes import MultinomialNB
>>> from sklearn.pipeline import Pipeline
>>> pipeline = Pipeline([('tfidf', TfidfTransformer()),
...                      ('chi2', SelectKBest(chi2, k=1000)),
...                      ('nb', MultinomialNB())])
>>> classif = SklearnClassifier(pipeline)

(Such a classifier could be trained on word counts for text classification.)
"""

from nltk.classify.api import ClassifierI
from nltk.probability import DictionaryProbDist

import numpy as np
from scipy.sparse import lil_matrix


class SklearnClassifier(ClassifierI):
    """Wrapper for scikit-learn classifiers."""

    def __init__(self, estimator, dtype=float, sparse=True):
        """
        :param estimator: scikit-learn classifier object.

        :param dtype: data type used when building feature array.
            scikit-learn estimators work exclusively on numeric data; use bool
            when all features are binary.

        :param sparse: Whether to use sparse matrices. The estimator must
            support these; not all scikit-learn classifiers do. The default
            value is True, since most NLP problems involve sparse feature sets.
        :type sparse: boolean.
        """
        self._clf = estimator
        self._dtype = dtype
        self._sparse = sparse

    def __repr__(self):
        return "<SklearnClassifier(%r)>" % self._clf

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
        """
        Train (fit) the scikit-learn estimator.

        :param labeled_featuresets: A list of classified featuresets,
            i.e., a list of tuples ``(featureset, label)``.
        """

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
        X = self._featuresets_to_array(featuresets)
        y = np.array([self._label_index[l] for l in labels])

        self._clf.fit(X, y)

        return self

    def _featuresets_to_array(self, featuresets):
        """Convert featureset to array or sparse matrix.

        Ignores features not seen during training.
        """

        if self._sparse:
            # XXX Transforming to lil_matrix is wasteful, since scikit-learn
            # estimators will typically convert to csr_matrix. Building a
            # csr_matrix directly would be more efficient (but also harder).
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
    try:
        from sklearn.linear_model.sparse import LogisticRegression
    except ImportError:     # separate sparse LR to be removed in 0.12
        from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import BernoulliNB

    print("scikit-learn Naive Bayes:")
    names_demo(SklearnClassifier(BernoulliNB(binarize=False), dtype=bool).train,
               features=binary_names_demo_features)
    print("scikit-learn logistic regression:")
    names_demo(SklearnClassifier(LogisticRegression(), dtype=np.float64).train,
               features=binary_names_demo_features)
