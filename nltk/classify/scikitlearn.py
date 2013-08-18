# Natural Language Toolkit: Interface to scikit-learn classifiers
#
# Author: Lars Buitinck <L.J.Buitinck@uva.nl>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
scikit-learn (http://scikit-learn.org) is a machine learning library for
Python. It supports many classification algorithms, including SVMs,
Naive Bayes, logistic regression (MaxEnt) and decision trees.

This package implement a wrapper around scikit-learn classifiers. To use this
wrapper, construct a scikit-learn estimator object, then use that to construct
a SklearnClassifier. E.g., to wrap a linear SVM with default settings:

>>> from sklearn.svm.sparse import LinearSVC
>>> from nltk.classify.scikitlearn import SklearnClassifier
>>> classif = SklearnClassifier(LinearSVC())

A scikit-learn classifier may include preprocessing steps when it's wrapped
in a Pipeline object. The following constructs and wraps a Naive Bayes text
classifier with tf-idf weighting and chi-square feature selection to get the
best 1000 features:

>>> from sklearn.feature_extraction.text import TfidfTransformer
>>> from sklearn.feature_selection import SelectKBest, chi2
>>> from sklearn.naive_bayes import MultinomialNB
>>> from sklearn.pipeline import Pipeline
>>> pipeline = Pipeline([('tfidf', TfidfTransformer()),
...                      ('chi2', SelectKBest(chi2, k=1000)),
...                      ('nb', MultinomialNB())])
>>> classif = SklearnClassifier(pipeline)
"""
from __future__ import print_function, unicode_literals

from nltk.classify.api import ClassifierI
from nltk.probability import DictionaryProbDist
from nltk import compat

try:
    import numpy as np
    from scipy.sparse import coo_matrix
except ImportError:
    pass

@compat.python_2_unicode_compatible
class SklearnClassifier(ClassifierI):
    """Wrapper for scikit-learn classifiers."""

    def __init__(self, estimator, dtype=float, sparse=True):
        """
        :param estimator: scikit-learn classifier object.

        :param dtype: data type used when building feature array.
            scikit-learn estimators work exclusively on numeric data. The
            default value should be fine for almost all situations.

        :param sparse: Whether to use sparse matrices. The estimator must
            support these; not all scikit-learn classifiers do. The default
            value is True, since most NLP problems involve sparse feature sets.
            Setting this to False may take a great amount of memory.
        :type sparse: boolean.
        """
        self._clf = estimator
        self._dtype = dtype
        self._sparse = sparse

    def __repr__(self):
        return "<SklearnClassifier(%r)>" % self._clf

    def batch_classify(self, featuresets):
        """Classify a batch of samples.

        :param labeled_featuresets: A list of featuresets, each a dict
            mapping strings to either numbers or booleans.
        :return: The predicted class label for each input sample.
        :rtype: list
        """
        X = self._convert(featuresets)
        y = self._clf.predict(X)
        return [self._index_label[int(yi)] for yi in y]

    def batch_prob_classify(self, featuresets):
        """Compute per-class probabilities for a batch of samples.

        :param labeled_featuresets: A list of featuresets, each a dict
            mapping strings to either numbers or booleans.
        :rtype: list of ``ProbDistI``
        """
        X = self._convert(featuresets)
        y_proba_list = self._clf.predict_proba(X)
        return [self._make_probdist(y_proba) for y_proba in y_proba_list]

    def labels(self):
        """The class labels used by this classifier.

        :rtype: list
        """
        return self._label_index.keys()

    def train(self, labeled_featuresets):
        """
        Train (fit) the scikit-learn estimator.

        :param labeled_featuresets: A list of ``(featureset, label)``
            where each ``featureset`` is a dict mapping strings to either
            numbers or booleans.
        """

        self._feature_index = {}
        self._index_label = []
        self._label_index = {}

        for fs, label in labeled_featuresets:
            for f in fs:
                if f not in self._feature_index:
                    self._feature_index[f] = len(self._feature_index)
            if label not in self._label_index:
                self._index_label.append(label)
                self._label_index[label] = len(self._label_index)

        featuresets, labels = zip(*labeled_featuresets)
        X = self._convert(featuresets)
        y = np.array([self._label_index[l] for l in labels])

        self._clf.fit(X, y)

        return self

    def _convert(self, featuresets):
        """Convert featuresets to a format scikit-learn will grok."""
        if self._sparse:
            return self._featuresets_to_coo(featuresets)
        else:
            return self._featuresets_to_array(featuresets)

    def _featuresets_to_coo(self, featuresets):
        """Convert featuresets to scipy.sparse matrix (COO format)."""

        i_ind = []
        j_ind = []
        values = []

        for i, fs in enumerate(featuresets):
            for f, v in compat.iteritems(fs):
                try:
                    j = self._feature_index[f]
                    i_ind.append(i)
                    j_ind.append(j)
                    values.append(self._dtype(v))
                except KeyError:
                    pass

        shape = (i + 1, len(self._feature_index))
        return coo_matrix((values, (i_ind, j_ind)), shape=shape,
                          dtype=self._dtype)

    def _featuresets_to_array(self, featuresets):
        """Convert featureset to NumPy array."""

        X = np.zeros((len(featuresets), len(self._feature_index)),
                     dtype=self._dtype)

        for i, fs in enumerate(featuresets):
            for f, v in compat.iteritems(fs):
                try:
                    X[i, self._feature_index[f]] = self._dtype(v)
                except KeyError:    # feature not seen in training
                    pass

        return X

    def _make_probdist(self, y_proba):
        return DictionaryProbDist(dict((self._index_label[i], p)
                                       for i, p in enumerate(y_proba)))


# skip doctests if scikit-learn is not installed
def setup_module(module):
    from nose import SkipTest
    try:
        import sklearn
    except ImportError:
        raise SkipTest("scikit-learn is not installed")

if __name__ == "__main__":
    from nltk.classify.util import names_demo, binary_names_demo_features
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import BernoulliNB

    print("scikit-learn Naive Bayes:")
    # Bernoulli Naive Bayes is designed for binary classification. We set the
    # binarize option to False since we know we're passing binary features
    # (when binarize=False, scikit-learn does x>0 on the feature values x).
    names_demo(SklearnClassifier(BernoulliNB(binarize=False), dtype=bool).train,
               features=binary_names_demo_features)
    print("scikit-learn logistic regression:")
    names_demo(SklearnClassifier(LogisticRegression(), dtype=np.float64).train,
               features=binary_names_demo_features)
