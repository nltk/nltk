# Natural Language Toolkit: Cosine Classifier
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Sam Huston <shuston@csse.unimelb.edu.au>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Cosine Classifier -- Beta version
"""

from math import sqrt, pow
from nltk.probability import *
from nltk_contrib.classify import *

class Cosine(AbstractClassify):
    """
    The Cosine Classifier uses the cosine distance algorithm to compute
    the distance between the sample document and each of the specified classes.
    A cosine classifier needs to be trained with representative examples
    of each class. From these examples the classifier
    calculates the most probable classification of the sample.
  
                     C . S
    D(C|S) = -------------------------
             sqroot(C^2) * sqroot (S^2)
  
    Internal data structures:
    _feature_dectector:
        holds a feature detector function
    _classes:
        holds a list of classes supplied during training
    _cls_freq_dist:
        holds a dictionary of Frequency Distributions,
        this structure is defined in probabilty.py in nltk
        this structure is indexed by class names and feature types
        the frequency distributions are indexed by feature values

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
        Train classifier using representative examples of classes;
        creates frequency distributions of these classes
            
        @param gold: dictionary mapping class names to representative examples
        """
        self._classes = []
        self._cls_freq_dist = {}
        for cls in gold:
            self._classes.append(cls)
            for (fname, fvals) in self._feature_detector(gold[cls]):
                self._cls_freq_dist[cls, fname] = FreqDist()
                for fval in fvals:
                    self._cls_freq_dist[cls, fname].inc(fval)



    def get_class_dict(self, sample):
        """
        @type sample: (any)
        @param sample: sample to be classified
        @return: Dictionary (class to probability)
        """
        return self._cosine(sample)

    def _cosine(self, sample):
        """
        @param sample: sample to be classified
        @return: Dictionary class to probability
            
            function uses sample to create a frequency distribution
            cosine distance is computed between each of the class distribustions
            and the sample's distribution
        """
        sample_vector_len = 0
        dot_prod = {}
        score = {}

        sample_dist = {}

        for (fname, fvals) in self._feature_detector(sample):
            sample_dist[fname] = FreqDist()
            for fval in fvals:
                sample_dist[fname].inc(fval)
         
        for cls in self._classes:
            dot_prod[cls] = 0

        for fname in sample_dist:
            for fval in sample_dist[fname].samples():
                #calculate the length of the sample vector
                sample_vector_len += pow(sample_dist[fname].count(fval), 2)

                for cls in self._classes:
                    if fval in self._cls_freq_dist[cls, fname].samples():
                        #calculate the dot product of the sample to each class
                        dot_prod[cls] += sample_dist[fname].count(fval) * self._cls_freq_dist[cls,fname].count(fval)


        for cls in self._classes:
            cls_vector_len = 0
            for fname in sample_dist:
                for fval in self._cls_freq_dist[cls, fname].samples():
                    #calculate the length of the class vector
                    cls_vector_len += pow(self._cls_freq_dist[cls, fname].count(fval), 2)
            
            #calculate the final score for this class 
            if sample_vector_len == 0 or cls_vector_len == 0:
                score[cls] = 0
            else :
                score[cls] = float(dot_prod[cls]) / (sqrt(sample_vector_len) * sqrt(cls_vector_len))
            
        return score

    def __repr__(self):
        return '<CosineClassifier: classes=%d>' % len(self._classes)  

##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////

def demo():
    from nltk_contrib import classify
    from nltk import detect
    
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))]})

    classifier = classify.cosine.Cosine(fd)
    training_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("a")

    for cls in result:
        print cls, ':', result[cls]
    
    """
    expected values:
    class a: 'a' = 6
             'b' = 1
         vector = 6^2 + 1^2 = 37
      b: 'a' = 1
         'b' = 6
         vector = 1^2 + 6^2 = 37
    sample: 'a' = 1
            vector = 1^2 = 1
    
    dot_prod a: 6*1
             b: 1*1

    score a: 6 / (sqrt(37) * sqrt(1)) = 0.98~
    score b: 1 / (sqrt(37) * sqrt(1)) =  0.16~
    """

   


def demo2():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"2-tup": lambda t: [t[n:n+2] for n in range(len(t)-1)]})

    classifier = classify.Cosine(fd)
    training_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("aaababb")

    for cls in result:
        print cls, ':', result[cls]
    """
    expected values:
    class a: 'aa' = 5
             'ab' = 1
         vector = 5^2 + 1^2 = 26
      b: 'bb' = 5
         'ba' = 1
         vector = 5^2 + 1^2 = 26
    sample: 'aa' = 2
            'ab' = 2
            'ba' = 1
            'bb' = 1
            vector = 2^2 + 2^2 + 1^2 + 1^2 = 10
    
    dot_prod a: 5*2 + 1*2
             b: 5*1 + 1*1

    score a: 12 / (sqrt(26) * sqrt(10)) = 0.74~
    score b: 6 / (sqrt(26) * sqrt(10))  = 0.37~
    """
    


def demo3():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))],
                          "2-tup": lambda t: [t[n:n+2] for n in range(len(t)-1)]})

    classifier = classify.Cosine(fd)
    training_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(training_data)

    result = classifier.get_class_dict("aaababb")

    for cls in result:
        print cls, ':', result[cls]

    """
    expected values:
    class a: 'a' = 6
             'b' = 1
             'aa' = 5
             'ab' = 1
         vector = 6^2 + 5^2 + 1 + 1 = 63
      b: 'a' = 1
         'b' = 6
         'bb' = 5
         'ba' = 1
         vector = 6^2 + 5^2 + 1 + 1 = 63
    sample: 'a' = 4
            'b' = 3
            'aa' = 2
            'ab' = 2
            'ba' = 1
            'bb' = 1
            vector = 4^2 + 3^2 + 2^2 + 2^2 + 1 + 1 = 35
    
    dot_prod a: 4*6 + 3*1 + 5*2 + 2*1 = 39
             b: 4*1 + 3*6 + 5*1 + 1*1 = 28

    score a: 39 / (sqrt(63) * sqrt(35)) = 0.83~
    score b: 28 / (sqrt(63) * sqrt(35)) = 0.59~
    """


def demo4():
    from nltk_contrib import classify
    from nltk import detect

    from nltk.corpora import genesis
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
