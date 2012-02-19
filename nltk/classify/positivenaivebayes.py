# Natural Language Toolkit: Positive Naive Bayes Classifier
#
# Copyright (C) 2012 NLTK Project
# Author: Alessandro Presta <alessandro.presta@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A variant of the Naive Bayes Classifier that performs binary classification with
partially-labeled training sets. In other words, assume we want to build a classifier
that assigns each example to one of two complementary classes (e.g., male names and
female names).
If we have a training set with labeled examples for both classes, we can use a
standard Naive Bayes Classifier. However, consider the case when we only have labeled
examples for one of the classes, and other, unlabeled, examples.
Then, assuming a prior distribution on the two labels, we can use the unlabeled set
to estimate the frequencies of the various features.

Let the two possible labels be 1 and 0, and let's say we only have examples labeled 1
and unlabeled examples. We are also given an estimate of P(1).

We compute P(feature|1) exactly as in the standard case.

To compute P(feature|0), we first estimate P(feature) from the unlabeled set (we are
assuming that the unlabeled examples are drawn according to the given prior distribution)
and then express the conditional probability as:

|                  P(feature) - P(feature|1) * P(1)
|  P(feature|0) = ----------------------------------
|                               P(0)
"""

from collections import defaultdict

from nltk.probability import FreqDist, ConditionalFreqDist, DictionaryProbDist, \
    ELEProbDist

from naivebayes import NaiveBayesClassifier

##//////////////////////////////////////////////////////
##  Positive Naive Bayes Classifier
##//////////////////////////////////////////////////////

class PositiveNaiveBayesClassifier(NaiveBayesClassifier):
    @staticmethod
    def train(positive_featuresets, unlabeled_featuresets, positive_prob_prior=0.5,
              estimator=ELEProbDist):
        """
        :param positive_featuresets: A list of featuresets that are known as positive
            examples (i.e., their label is ``True``).

        :param unlabeled_featuresets: A list of featuresets whose label is unknown.

        :param positive_prob_prior: A prior estimate of the probability of the label
            ``True`` (default 0.5).
        """
        positive_feature_freqdist = ConditionalFreqDist()
        unlabeled_feature_freqdist = ConditionalFreqDist()
        feature_values = defaultdict(set)
        fnames = set()
        
        for featureset in positive_featuresets:
            for fname, fval in featureset.items():
                positive_feature_freqdist[fname].inc(fval)
                feature_values[fname].add(fval)
                fnames.add(fname)
                
        for featureset in unlabeled_featuresets:
            for fname, fval in featureset.items():
                unlabeled_feature_freqdist[fname].inc(fval)
                feature_values[fname].add(fval)
                fnames.add(fname)

        num_positive_examples = len(positive_featuresets)
        for fname in fnames:
            count = positive_feature_freqdist[fname].N()
            positive_feature_freqdist[fname].inc(None, num_positive_examples-count)
            feature_values[fname].add(None)

        num_unlabeled_examples = len(unlabeled_featuresets)
        for fname in fnames:
            count = unlabeled_feature_freqdist[fname].N()
            unlabeled_feature_freqdist[fname].inc(None, num_unlabeled_examples-count)
            feature_values[fname].add(None)

        negative_prob_prior = 1.0 - positive_prob_prior
        label_probdist = DictionaryProbDist({True: positive_prob_prior,
                                             False: negative_prob_prior})
            
        feature_probdist = {}
        for fname, freqdist in positive_feature_freqdist.items():
            probdist = estimator(freqdist, bins=len(feature_values[fname]))
            feature_probdist[True, fname] = probdist

        for fname, freqdist in unlabeled_feature_freqdist.items():
            global_probdist = estimator(freqdist, bins=len(feature_values[fname]))
            negative_feature_probs = {}
            for fval in feature_values[fname]:
                prob = (global_probdist.prob(fval)
                        - positive_prob_prior *
                        feature_probdist[True, fname].prob(fval)) \
                        / negative_prob_prior
                negative_feature_probs[fval] = max(prob, 0.0)
            feature_probdist[False, fname] = DictionaryProbDist(negative_feature_probs)

        return NaiveBayesClassifier(label_probdist, feature_probdist)
                                                 
##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    from nltk.classify.util import pnb_demo
    classifier = pnb_demo(PositiveNaiveBayesClassifier.train)
    classifier.show_most_informative_features()

if __name__ == '__main__':
    demo()
            


        
