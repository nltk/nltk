# Natural Language Toolkit: Naive Bayes Classifier
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Sam Huston <shuston@csse.unimelb.edu.au>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Naive Bayes Classifier -- Beta version
"""

from operator import itemgetter
from nltk.probability import *
from nltk_contrib.classify import *

class NaiveBayes(AbstractClassify):
    """
    The Naive Bayes Classifier is a supervised classifier.
    It needs to be trained with representative examples of 
    each class. From these examples the classifier
    calculates the most probable classification of the sample.

  
                          P(class) * P(features|class)
    P(class|features) =    -------------------------
                                  P(features)
    
    Internal data structures:
    _feature_dectector:
        holds a feature detector function
    _classes:
        holds a list of classes supplied during training
    _cls_prob_dist:
        hols a Probability Distribution, namely GoodTuringProbDist
        this structure is defined in probabilty.py in nltk
        this structure is indexed by classnames
    _feat_prob_dist:
        holds Conditional Probability Distribution, conditions are 
        class name, and feature type name
        these probability distributions are indexed by feature values
        this structure is defined in probabilty.py in nltk
    """

    def __init__(self, feature_detector):
        """
        @param feature_detector: feature detector produced function, which takes
        a sample of object to be classified (eg: string or list of words) and returns
        a list of tuples (feature_type_name, list of values of this feature type)
        """
        self._feature_detector = feature_detector

    def train(self, gold):
        """
        @param gold: dictionary of class names to representative examples
            function takes representative examples of classes
            then creates frequency distributions of these classes
            these freqdists are used to create probability distributions
        """
        cls_freq_dist = FreqDist()
        feat_freq_dist = ConditionalFreqDist()
        self._classes = []
        feature_values = {}

        for cls in gold:
            self._classes.append(cls)
            for (fname, fvals) in self._feature_detector(gold[cls]):
                for fval in fvals:
                    #increment number of tokens found in a particular class
                    cls_freq_dist.inc(cls)

                    #increment number of features found in (class, feature type)
                    feat_freq_dist[cls, fname].inc(fval)

                    #record that fname can be associated with this feature 
                    if fname not in feature_values: feature_values[fname] = set()
                    feature_values[fname].add(fval)

        # convert the frequency distributions to probability distribution for classes
        self._cls_prob_dist = GoodTuringProbDist(cls_freq_dist, cls_freq_dist.B())
        
        # for features
        def make_probdist(freqdist, (cls, fname)):
            return GoodTuringProbDist(freqdist, len(feature_values[fname]))
        self._feat_prob_dist = ConditionalProbDist(feat_freq_dist, make_probdist, True)
        
    def get_class_dict(self, sample):
        """
        @param sample: sample to be classified
        @ret: Dictionary (class to probability)
        """
        return self._naivebayes(sample)

    def _naivebayes(self, sample):
        """
        @param sample: sample to be tested
        @ret: Dictionary (class to probability)
        
            naivebayes classifier:
            creates a probability distribution based on sample string

            sums the log probabilities of each feature value 
                for each class and feature type
                and with the probability of the resepective class
        """
        sample_feats = self._feature_detector(sample)

        logprob_dict = {}
        score = {}
        for cls in self._classes:
            # start with the probability of each class
            logprob_dict[cls] = self._cls_prob_dist.prob(cls)
    
        for fname, fvals in sample_feats:
            for cls in self._classes:
                probdist = self._feat_prob_dist[cls, fname]
                for fval in fvals:
                    if fval in probdist.samples():
                        logprob_dict[cls] += probdist.logprob(fval)

        dicttmp = DictionaryProbDist(logprob_dict, normalize=True, log=True)
        for sample in dicttmp.samples():
            score[sample] = dicttmp.prob(sample) 
            
        return score

    def __repr__(self):
        return '<NaiveBayesClassifier: classes=%d>' % len(self._classes)  


##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////


def demo():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"1-tup": lambda t: list(t)})

    classifier = classify.NaiveBayes(fd)
    training_data = {"class a": "aaaaaab",
                     "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("a")

    for cls in result:
        print cls, ':', result[cls]
    
    """
    expected values:
    class_probs a = 0.5
                b = 0.5
    class a: 'a' = 6/7
             'b' = 1/7
      b: 'a' = 1/7
         'b' = 6/7
    sample: 'a' = 1
    
    score a: 0.5 * 6/7 = 0.42~
    score b: 0.5 * 1/7 = 0.07~
    """   


def demo2():
    from nltk_contrib import classify
    from nltk import detect
 
    fd = detect.feature({"2-tup": lambda t: [t[n:n+2] for n in range(len(t))]})

    classifier = classify.NaiveBayes(fd)
    training_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("aababb")

    for cls in result:
        print cls, ':', result[cls]
    """
    expected values:
    class_probs a = 0.5
                b = 0.5
    class a: 'aa' = 5/6
             'ab' = 1/6
          b: 'bb' = 5/6
             'ba' = 1/6
    sample: 'aa' = 2
            'ab' = 2
            'ba' = 1
            'bb' = 1
    
    score a: 0.5 * 5/6 * 5/6 * 1/6 * 1/6 = 0.09~
    score b: 0.5 * 5/6 * 1/6 = 0.06~
    """
    


def demo3():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))],
                          "2-tup": lambda t: [t[n:n+2] for n in range(len(t))]})

    classifier = classify.NaiveBayes(fd)
    training_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("aaababb")

    for cls in result:
        print cls, ':', result[cls]

    """
    expected values:
    class_probs a = 0.5
                b = 0.5
    class a: 'a' = 6/7
             'b' = 1/7
             'aa' = 5/6
             'ab' = 1/6
      b: 'a' = 1/7
         'b' = 6/7
         'bb' = 5/6
         'ba' = 1/6
    sample: 'a' = 4
            'b' = 3
            'aa' = 2
            'ab' = 2
        'ba' = 1
        'bb' = 1
    
    score a: 0.5 * 6/7^4 * 1/7^3 * 5/6^2 * 1/6^2 = 1.5 e-5
    score b: 0.5 * 1/7^4 * 6/7^3 * 5/6 * 1/6 = 0.0014~
    """

def demo4():
    from nltk_contrib import classify
    from nltk import detect

    from nltk.corpora import genesis
    from itertools import islice
  
    fd = detect.feature({"2-tup": lambda t: [' '.join(t)[n:n+2] for n in range(len(' '.join(t))-1)],
                     "words": lambda t: t})

    classifier = classify.NaiveBayes(fd)
    training_data = {}
    training_data["english-kjv"] = list(islice(genesis.raw("english-kjv"), 0, 400))
    training_data["french"] = list(islice(genesis.raw("french"), 0, 400))
    training_data["finnish"] = list(islice(genesis.raw("finnish"), 0, 400))

    classifier.train(training_data)

    result = classifier.get_class_probs(list(islice(genesis.raw("english-kjv"), 150, 200)))

    print 'english-kjv :', result.prob('english-kjv')
    print 'french :', result.prob('french')
    print 'finnish :', result.prob('finnish')

if __name__ == '__main__':
    demo2()
