from math import sqrt, pow
from nltk_lite.probability import *
from nltk_lite.classify import *

class Cosine(AbstractClassify):
    """
    The Cosine Classifier uses the cosine distance algorithm to compute
    the distance between the sample document and each of the specified classes.
    Cosine classification is a supervised classifier. It needs to be trained
    with representative examples of each class. From these examples the classifier
    calculates the most probable classification of the sample.

  
                     C . S
    D(C|S) = -------------------------
             sqroot(C^2) * sqroot (S^2)
  

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
        trains the classifier
        @param classes: dictionary of class names to representative examples
        """
        self._classes = []
        self._cls_freq_dist = {}
        for cls in gold:
            self._classes.append(cls)
            self._cls_freq_dist[cls] = FreqDist() 
            feats_list = []
            for (fname, fvals) in self._feature_detector(gold[cls]):
                for feature in fvals:
                    self._cls_freq_dist[cls].inc(feature)


    def get_class_probs(self, sample):
        """
        @param text: sample to be classified
        @ret: DictionaryProbDist (class to probability)
              see probability.py
        """
        return self._cosine(sample)

    def _cosine(self, sample):
        """
        @param text: sample to be classified
        @ret: DictionaryProbDist (class to probability)
        """
        sample_word_count = 0
        dot_prod = {}
        class_word_count = {}
        score = {}
        sample_dist = FreqDist()

        for (fname, fvals) in self._feature_detector(sample):
            for feature in fvals:
                sample_dist.inc(feature)

        for feature in sample_dist.samples():
            #calculate the length of the sample vector
            sample_word_count += pow(sample_dist.freq(feature), 2)

            for cls in self._classes:
                dot_prod[cls] = 0
                if feature in self._cls_freq_dist[cls].samples():
                    #calculate the dot product of the sample to each class
                    dot_prod[cls] += sample_dist.freq(feature) * self._cls_freq_dist[cls].freq(feature)
    
        for cls in self._classes:
            cls_word_count = 0
            for feature in self._cls_freq_dist[cls].samples():
                #calculate the length of the example vector
                cls_word_count += pow(self._cls_freq_dist[cls].freq(feature), 2)
            score[cls] = dot_prod[cls] / (sqrt(sample_word_count) * sqrt(cls_word_count))

        return DictionaryProbDist(score, normalize=True)

###########################################################

def demo():
    from nltk_lite import detect, classify
    from nltk_lite.corpora import genesis
    from itertools import islice

    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))]})

    classifier = classify.Cosine(fd)
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

    classifier = classify.Cosine(fd)
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
