# Natural Language Toolkit: Spearman Rank Correlation classifier
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Sam Huston <shuston@csse.unimelb.edu.au>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Spearman Classifier -- Beta version
"""

from math import pow
from nltk.probability import *
from nltk_contrib.classify import *

class Spearman(AbstractClassify):
    """
    The Spearman-rho Classifier is a non-parametric measure of correlation between two
    sets of ranked values
    Spearman-rho classification is a supervised classifier. It needs to be trained
    with representative examples of each class. From these examples the classifier
    calculates the most probable classification of the sample.
  
                    6 * sum((Ai - Bi)^2)
    p = 1   -     -------------------------
                       (n^3) - n
                       
    where A, B are the vectors of ranked objects
             n is the number of ranked objects being compared
  
    Internal data structures:
    _feature_dectector:
        holds a feature detector function
    _classes:
        holds a list of classes supplied during trainning
    _cls_rank:
        holds a dictionary of ordered lists,   
        the order of the list is deturnmined by:
        first ranked object is ordered first
        duplicate values are ordered in alphabetical order
    """

    def __init__(self, feature_detector, crop_data=100):
        """
        @param feature_detector: feature detector produced function
        @param crop_data: ranking beyond which features are ignored
                          this produces a maximum rank for large data sets
                          where the lower order values would offset the results
        """
        self._feature_detector = feature_detector
        self._crop_data = crop_data
   

    def train(self, gold):
        """
        trains the classifier
        @param classes: dictionary of class names to representative examples

            function takes representative examples of classes
            then creates ordered lists of ranked features
            indexed by class name and feature type
        """

        self._classes = []
        self._cls_rank = {}

        for cls in gold:
            self._classes.append(cls)
            for (fname, fvals) in self._feature_detector(gold[cls]):
                cls_freq_dist = FreqDist()
                for fval in fvals:
                    cls_freq_dist.inc(fval)
                self._cls_rank[cls, fname] = self._get_ranks(cls_freq_dist)


    def get_class_dict(self, sample):
        """
        @param text: sample to be classified
        @ret: Dictionary (class to probability)
        """
        return self._spearman_ranked(sample)


    def _spearman_ranked(self, sample):
        """
        @param text: sample to be classified
        @ret: Dictionary class to probability
            
            function uses sample to create an ordered list of ranked features
            the spearman-rho formula is then applied to produce a correlation
            
            a union operation is used to create two lists of the same length for the formula
            missing values are appended to each list in alphabetical order
        """

        rank_diff = {}
        score = {}
        sample_rank = {}
        totalfvals = {}
        
        for (fname, fvals) in self._feature_detector(sample):
            sample_dist = FreqDist()
            for fval in fvals:
                sample_dist.inc(fval)
            sample_rank[fname] = self._get_ranks(sample_dist)
        

        for cls in self._classes:
            rank_diff[cls] = 0
            totalfvals[cls] = 0
    
        for fname in sample_rank:
            for cls in self._classes:
                tmp_clslist = self._cls_rank[cls, fname]
                tmp_smplist = sample_rank[fname]
                
                # take the union of the the class and sample lists, append each in alphabetical order
                
                tmp_clslist.extend(list(set(tmp_smplist).difference(set(tmp_clslist))))
                tmp_smplist.extend(list(set(tmp_clslist).difference(set(tmp_smplist))))            
                
                totalfvals[cls] += len(tmp_clslist)
                
                for fval in tmp_smplist:
                    rank_diff[cls] += pow(tmp_smplist.index(fval) - tmp_clslist.index(fval), 2)

        for cls in self._classes:
            score[cls] = 1 - (float(6 * rank_diff[cls]) / (pow(totalfvals[cls], 3) - totalfvals[cls]))

        return score



    def _get_ranks(self, sample_dist):
        """
        @param sample_dist: sample frequency distribution
        @ret: ordered list of features.
        """

        samples = sample_dist.samples()
        ordered_list = [item for (freq, item) in sorted([(sample_dist.count(item),item) for item in samples], reverse=True)]      
        return ordered_list[:self._crop_data] 
        
    def __repr__(self):
        return '<SpearmanClassifier: classes=%d>' % len(self._classes)          

###########################################################

def demo():
    from nltk_contrib import classify
    from nltk import detect
    
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))]})

    classifier = classify.spearman.Spearman(fd)
    trainning_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(trainning_data)

    result = classifier.get_class_dict("a")

    for cls in result:
        print cls, ':', result[cls]
    """
    expected values:
    class a: 'a' = 1
             'b' = 2
          b: 'a' = 2
             'b' = 1
    sample: 'a' = 1
   
    score a: 6*(0^2) / 8-2= 0
    score b: 6*(1^2) / 8-2 = 1
    """


def demo2():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"2-tup": lambda t: [t[n:n+2] for n in range(len(t)-1)]})

    classifier = classify.spearman.Spearman(fd)
    trainning_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(trainning_data)

    result = classifier.get_class_dict("aaababb")

    for cls in result:
        print cls, ':', result[cls]
    """
    expected values:
    class a: 'aa' = 1
             'ab' = 2
          b: 'bb' = 1
             'ba' = 2
    sample: 'aa' = 1
            'ab' = 1
            'ba' = 2
            'bb' = 2
    

    score a: 1/ 1+0+1+5+5 = 0.5
    score b: 1/ 1+1+0+6+6 = 0.5
    """
    


def demo3():
    from nltk_contrib import classify
    from nltk import detect
  
    fd = detect.feature({"1-tup": lambda t: [t[n] for n in range(len(t))],
                          "2-tup": lambda t: [t[n:n+2] for n in range(len(t)-1)]})

    classifier = classify.spearman.Spearman(fd)
    trainning_data = {"class a": "aaaaaab",
                      "class b": "bbbbbba"}
    classifier.train(trainning_data)

    result = classifier.get_class_dict("aaababb")

    for cls in result:
        print cls, ':', result[cls]

    """
    expected values:
    class a: 'a' = 1
             'b' = 3
             'aa' = 2
             'ab' = 3
          b: 'a' = 3
             'b' = 1
             'bb' = 2
             'ba' = 3
    sample: 'a' = 1
            'b' = 2
            'aa' = 3
            'ab' = 3
            'ba' = 4
            'bb' = 4

    score a: 1/ 1+0+1+1+0+3+3 = 1/ 9
    score b: 1/ 1+2+1+2+1+4+4 = 1/ 15
    """


def demo4():
    from nltk_contrib import classify
    from nltk import detect

    from nltk.corpora import genesis
    from itertools import islice

    fd = detect.feature({"2-tup": lambda t: [' '.join(t)[n:n+2] for n in range(len(' '.join(t))-1)],
                     "words": lambda t: t})

    classifier = classify.spearman.Spearman(fd)
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
