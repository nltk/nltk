from operator import itemgetter
from nltk_lite.probability import *
from nltk_lite.classify import *

class NaiveBayes(AbstractClassify):
    """
    The Naive Bayes Classifier is a supervised classifier.
    It needs to be trained with representative examples of 
    each class. From these examples the classifier
    calculates the most probable classification of the sample.

  
                          P(class) * P(features|class)
    P(class|features) =    -------------------------
                                  P(features)
    
    """

    def __init__(self, feature_detector):
        """
        @param feature_detector: feature detector produced function
        @param of feature detector: sample of object to be classified
                                    eg: string or list of words
        @ret of feature detector: list of tuples
                   (feature_name, list of values of this feature type)
        """
        self._feature_detector = feature_detector

    def train(self, gold):
        """
        @param classes: dictionary of class names to representative examples
        """
        cls_freq_dist = FreqDist()
        feat_freq_dist = ConditionalFreqDist()
        self._classes = []
        feature_values = {}

        for cls in gold:
            self._classes.append(cls)
            for (fname, fvals) in self._feature_detector(gold[cls]):
                for feature in fvals:
                    #increment number of tokens found in a particular class
                    cls_freq_dist.inc(cls)

                    #increment number of features found in (class, feature type)
                    feat_freq_dist[cls, fname].inc(feature)

                    #record that fname can be associated with this feature 
                    if fname not in feature_values: feature_values[fname] = set()
                    feature_values[fname].add(feature)

        # convert the frequency distributions to probability distribution for classes
        self._cls_prob_dist = MLEProbDist(cls_freq_dist)
    
        # for features
        self._feat_prob_dist = ConditionalProbDist(feat_freq_dist, MLEProbDist)
    
    def get_class_probs(self, sample):
        """
        @param text: sample to be classified
        @ret: DictionaryProbDist (class to probability)
              see probability.py
        """
        return self._naivebayes_classification(sample)


    def _naivebayes_classification(self, sample):
        """
        @param sample: sample to be tested
        @ret: DictionaryProbDist (class to probability)
        """
        sample_feats = self._feature_detector(sample)

        logprob_dict = {}
        for cls in self._classes:
            # start with the probability of each class
            logprob_dict[cls] = self._cls_prob_dist.logprob(cls)
    
        for fname, fvals in sample_feats:
            for cls in self._classes:
                probdist = self._feat_prob_dist[cls, fname]
                for feature in fvals:
                    if feature in probdist.samples():
                        # add the log probability of each 
                        # feature in both the sample and the class
                        logprob_dict[cls] += probdist.logprob(feature)

        return DictionaryProbDist(logprob_dict, normalize=True, log=True)

################################################################

def demo():
    from nltk_lite import detect, classify
    from nltk_lite.corpora import genesis
    from itertools import islice
  
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))]})

    classifier = classify.NaiveBayes(fd)
    training_data = {"class a": "a a a a a a b",
                      "class b": "b b b b b b a"}
    classifier.train(training_data)

    result = classifier.get_class_probs("a")

    print 'class a :', result.prob('class a')
    print 'class b :', result.prob('class b')


def demo2():
    from nltk_lite import detect, classify
    from nltk_lite.corpora import genesis
    from itertools import islice
  
    fd = detect.feature({"2-tup": lambda t: [' '.join(t)[n:n+2] for n in range(len(' '.join(t))-1)],
	                 "words": lambda t: t})

    classifier = classify.NaiveBayes(fd)
    training_data = {}
    training_data["english-kjv"] = list(islice(genesis.raw("english-kjv"), 0, 400))
    training_data["french"] = list(word for word in islice(genesis.raw("french"), 0, 400))
    training_data["finnish"] = list(word for word in islice(genesis.raw("finnish"), 0, 400))

    classifier.train(training_data)

    result = classifier.get_class_probs(list(islice(genesis.raw("english-kjv"), 150, 200)))

    print 'english-kjv :', result.prob('english-kjv')
    print 'french :', result.prob('french')
    print 'finnish :', result.prob('finnish')

if __name__ == '__main__':
    demo2()
