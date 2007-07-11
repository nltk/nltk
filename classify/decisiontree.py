# Natural Language Toolkit: Decision Tree Classifiers
#
# Copyright (C) 2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: naivebayes.py 2063 2004-07-17 21:02:24Z edloper $

"""
A classifier model that decides which label to assign to a token on
the basis of a tree structure, where branches correspond to conditions
on feature values, and leaves correspond to label assignments.
"""

from nltk.classify.api import *
from nltk.probability import *
from nltk import defaultdict

class DecisionTree(ClassifierI):
    def __init__(self, label, feature_name=None, decisions=None):
        self._label = label
        self._fname = feature_name
        self._decisions = decisions

    def classify(self, token):
        # Decision leaf:
        if self._fname is None:
            return self._label

        # Decision tree:
        fval = token[self._fname]
        if fval in self._decisions:
            return self._decisions[fval].classify(token)
        else:
            return self._label

    def error(self, tokens):
        errors = 0
        for token, label in tokens:
            if self.classify(token) != label:
                errors += 1
        return float(errors)/len(tokens)

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
    def train(training_tokens, entropy_cutoff=0.05, depth_cutoff=100):
        # Collect a list of all feature names.
        feature_names = set()
        for token, label in training_tokens:
            for fname in token:
                feature_names.add(fname)

        # Start with a stump..
        tree = DecisionTree.best_stump(feature_names, training_tokens)

        tree.refine(training_tokens, entropy_cutoff, depth_cutoff-1)

        # Return it
        return tree

    @staticmethod
    def leaf(training_tokens):
        label = FreqDist([label for (tok,label) in training_tokens]).max()
        return DecisionTree(label)

    @staticmethod
    def stump(feature_name, training_tokens):
        label = FreqDist([label for (tok,label) in training_tokens]).max()

        # Find the best label for each value.
        freqs = defaultdict(FreqDist) # freq(label|value)
        for tok, label in training_tokens:
            feature_value = tok[feature_name]
            freqs[feature_value].inc(label)

        decisions = dict([(val, DecisionTree(freqs[val].max()))
                          for val in freqs])
        return DecisionTree(label, feature_name, decisions)

    def refine(self, training_tokens, entropy_cutoff, depth_cutoff):
        if self._fname is None: return
        if depth_cutoff <= 0: return
        for fval in self._decisions:
            fval_toks = [(tok,label) for (tok,label) in training_tokens
                         if tok[self._fname] == fval]

            label_freqs = FreqDist([label for (tok,label) in fval_toks])
            if entropy(MLEProbDist(label_freqs)) > entropy_cutoff:
                self._decisions[fval] = DecisionTree.train(
                    fval_toks, entropy_cutoff, depth_cutoff)

    @staticmethod
    def best_stump(feature_names, training_tokens):
        best_stump = DecisionTree.leaf(training_tokens)
        best_error = best_stump.error(training_tokens)
        for fname in feature_names:
            stump = DecisionTree.stump(fname, training_tokens)
            stump_error = stump.error(training_tokens)
            if stump_error < best_error:
                best_error = stump_error
                best_stump = stump
        print ('best stump for %4d toks uses %20s err=%6.4f' %
               (len(training_tokens), best_stump._fname, stump_error))
        return best_stump

##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    from nltk.classify.util import names_demo, binary_names_demo_features
    classifier = names_demo(DecisionTree.train, binary_names_demo_features)
    print classifier.pp(depth=7)

if __name__ == '__main__':
    demo()
                             
