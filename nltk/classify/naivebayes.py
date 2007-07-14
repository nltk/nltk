# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: naivebayes.py 2063 2004-07-17 21:02:24Z edloper $

"""
::
                      P(label) * P(f1|label) * ... * P(fn|label)
 P(label|features) = -------------------------------------------
                                        P(features)

"""

from nltk.classify.api import *
from nltk.probability import *
from nltk import defaultdict

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NaiveBayesClassifier(ClassifyI):
    """
    A Naive Bayes classifier.
    """
    def __init__(self, label_probdist, feature_probdist):
        """
        @param label_probdist: P(label)
        @param feature_probdist: P(fval|label,f)
        """
        self._label_probdist = label_probdist
        self._feature_probdist = feature_probdist
        self._labels = label_probdist.samples()

    def labels(self):
        return self._labels

    def classify(self, featureset):
        if isinstance(featureset, list): # Handle batch mode.
            return [self.classify(fs) for fs in featureset]
        
        return self.probdist(featureset).max()
        
    def probdist(self, featureset):
        if isinstance(featureset, list): # Handle batch mode.
            return [self.probdist(fs) for fs in featureset]
                
        # Find the log probabilty of each label, given the features.
        logprob = {}
        for label in self._labels:
            logprob[label] = self._label_probdist.logprob(label)

        for label in self._labels:
            for (fname, fval) in featureset.items():
                if (label, fname) in self._feature_probdist:
                    feature_probs = self._feature_probdist[label,fname]
                    logprob[label] += feature_probs.logprob(fval)

        return DictionaryProbDist(logprob, normalize=True, log=True)

    def show_most_informative_features(self, n=10):
        # Determine the most relevant features, and display them.
        cpdist = self._feature_probdist
        print '\nMost Informative Features    ',
        print 'P(fval|Male) : P(fval|Female)\n'+'-'*60
        for (fname, fval) in self.most_informative_features(10):
            m = cpdist['male',fname].prob(fval)
            f = cpdist['female',fname].prob(fval)
            if m == f:
                print '%14s = %-7r  %16d : %d' % (fname, fval, 1, 1)
            if m > f:
                print '%14s = %-7r  %16.1f : %d' % (fname, fval, m/f, 1)
            else:
                print '%14s = %-7r  %16d : %.1f' % (fname, fval, 1, f/m)

    def most_informative_features(self, n=100):
        """
        Return a list of the 'most informative' features used by this
        classifier.  For the purpose of this function, the
        informativeness of a feature C{(fname,fval)} is equal to the
        highest value of P(fname=fval|label), for any label, divided by
        the lowest value of P(fname=fval|label), for any label.

          max[ P(fname=fval|label1) / P(fname=fval|label2) ]
        """
        # The set of (fname, fval) pairs used by this classifier.
        features = set()
        # The max & min probability associated w/ each (fname, fval)
        # pair.  Maps (fname,fval) -> float.
        maxprob = defaultdict(lambda: 0.0)
        minprob = defaultdict(lambda: 1.0)

        for (label, fname), probdist in self._feature_probdist.items():
            for fval in probdist.samples():
                feature = (fname, fval)
                features.add( feature )
                p = probdist.prob(fval)
                maxprob[feature] = max(p, maxprob[feature])
                minprob[feature] = min(p, minprob[feature])
                if minprob[feature] == 0:
                    features.discard(feature)

        # Convert features to a list, & sort it by how informative
        # features are.
        features = sorted(features, 
            key=lambda feature: minprob[feature]/maxprob[feature])
        return features[:n]

    @staticmethod
    def train(labeled_featuresets, estimator=ELEProbDist):
        """
        @param labeled_featuresets: A list of classified featuresets,
            i.e., tuples C{(featureset, label)}.
        """
        label_freqdist = FreqDist()
        feature_freqdist = defaultdict(FreqDist)
        feature_values = defaultdict(set)

        for featureset, label in labeled_featuresets:
            label_freqdist.inc(label)
            
            for fname, fval in featureset.items():
                # Increment freq(fval|label, fname)
                feature_freqdist[label, fname].inc(fval)
                # Record that fname can take the value fval.
                feature_values[fname].add(fval)

        # Create the P(label) distribution
        label_probdist = estimator(label_freqdist)

        # Create the P(fval|label, fname) distribution
        feature_probdist = {}
        for ((label, fname), freqdist) in feature_freqdist.items():
            probdist = estimator(freqdist, bins=len(feature_values[fname]))
            feature_probdist[label,fname] = probdist

        return NaiveBayesClassifier(label_probdist, feature_probdist)

##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    from nltk.classify.util import names_demo
    classifier = names_demo(NaiveBayesClassifier.train)
    classifier.show_most_informative_features()
    
if __name__ == '__main__':
    demo()
    
    
