# Natural Language Toolkit: Decision Tree Classifiers
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: naivebayes.py 2063 2004-07-17 21:02:24Z edloper $

"""
A classifier model that decides which label to assign to a token on
the basis of a tree structure, where branches correspond to conditions
on feature values, and leaves correspond to label assignments.
"""

from nltk.probability import *
from nltk import defaultdict

from api import *

class DecisionTreeClassifier(ClassifierI):
    def __init__(self, label, feature_name=None, decisions=None):
        self._label = label
        self._fname = feature_name
        self._decisions = decisions

    def labels(self):
        labels = [self._label]
        if self._decisions is not None:
            for dt in self._decisions.values():
                labels.extend(dt.labels())
        return list(set(labels))

    def classify(self, featureset):
        # Decision leaf:
        if self._fname is None:
            return self._label

        # Decision tree:
        fval = featureset[self._fname]
        if fval in self._decisions:
            return self._decisions[fval].classify(featureset)
        else:
            return self._label

    def error(self, labeled_featuresets):
        errors = 0
        for featureset, label in labeled_featuresets:
            if self.classify(featureset) != label:
                errors += 1
        return float(errors)/len(labeled_featuresets)

    def pp(self, width=70, prefix='', depth=4):
        if self._fname is None:
            n = width-len(prefix)-15
            return '%s%s %s\n' % (prefix, '.'*n, self._label)
        s = ''
        for i, (fval, result) in enumerate(sorted(self._decisions.items())):
            hdr = '%s%s=%s? ' % (prefix, self._fname, fval)
            n = width-15-len(hdr)
            s += '%s%s %s\n' % (hdr, '.'*(n), result._label)
            if result._fname is not None and depth>1:
                s += result.pp(width, prefix+'  ', depth-1)
        return s

    def __str__(self):
        return self.pp()

    @staticmethod
    def train(labeled_featuresets, entropy_cutoff=0.05, depth_cutoff=100,
              support_cutoff=10):
        # Collect a list of all feature names.
        feature_names = set()
        for featureset, label in labeled_featuresets:
            for fname in featureset:
                feature_names.add(fname)

        # Start with a stump..
        tree = DecisionTreeClassifier.best_stump(
            feature_names, labeled_featuresets)

        tree.refine(labeled_featuresets, entropy_cutoff, depth_cutoff-1,
                    support_cutoff)

        # Return it
        return tree

    @staticmethod
    def leaf(labeled_featuresets):
        label = FreqDist([label for (featureset,label)
                          in labeled_featuresets]).max()
        return DecisionTreeClassifier(label)

    @staticmethod
    def stump(feature_name, labeled_featuresets):
        label = FreqDist([label for (featureset,label)
                          in labeled_featuresets]).max()

        # Find the best label for each value.
        freqs = defaultdict(FreqDist) # freq(label|value)
        for featureset, label in labeled_featuresets:
            feature_value = featureset[feature_name]
            freqs[feature_value].inc(label)

        decisions = dict([(val, DecisionTreeClassifier(freqs[val].max()))
                          for val in freqs])
        return DecisionTreeClassifier(label, feature_name, decisions)

    def refine(self, labeled_featuresets, entropy_cutoff, depth_cutoff,
               support_cutoff):
        if len(labeled_featuresets) <= support_cutoff: return
        if self._fname is None: return
        if depth_cutoff <= 0: return
        for fval in self._decisions:
            fval_featuresets = [(featureset,label) for (featureset,label) 
                                in labeled_featuresets
                                if featureset[self._fname] == fval]

            label_freqs = FreqDist([label for (featureset,label)
                                    in fval_featuresets])
            if entropy(MLEProbDist(label_freqs)) > entropy_cutoff:
                self._decisions[fval] = DecisionTreeClassifier.train(
                    fval_featuresets, entropy_cutoff, depth_cutoff)

    @staticmethod
    def best_stump(feature_names, labeled_featuresets):
        best_stump = DecisionTreeClassifier.leaf(labeled_featuresets)
        best_error = best_stump.error(labeled_featuresets)
        for fname in feature_names:
            stump = DecisionTreeClassifier.stump(fname, labeled_featuresets)
            stump_error = stump.error(labeled_featuresets)
            if stump_error < best_error:
                best_error = stump_error
                best_stump = stump
        print ('best stump for %4d toks uses %20s err=%6.4f' %
               (len(labeled_featuresets), best_stump._fname, best_error))
        return best_stump

##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    from nltk.classify.util import names_demo, binary_names_demo_features
    classifier = names_demo(DecisionTreeClassifier.train,
                            binary_names_demo_features)
    print classifier.pp(depth=7)

if __name__ == '__main__':
    demo()
                             
