from collections import defaultdict

from nltk.probability import FreqDist, ConditionalFreqDist, DictionaryProbDist, \
    ELEProbDist

from naivebayes import NaiveBayesClassifier

class PositiveNaiveBayesClassifier(NaiveBayesClassifier):
    """

    """
    @staticmethod
    def train(positive_featuresets, unlabeled_featuresets, positive_prob_prior=0.5,
              estimator=ELEProbDist):
        """

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
    from util import pnb_demo#from nltk.classify.util import pnb_demo
    classifier = pnb_demo(PositiveNaiveBayesClassifier.train)
    classifier.show_most_informative_features()

if __name__ == '__main__':
    demo()
            


        
