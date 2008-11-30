# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Sam Huston <shuston@csse.unimelb.edu.au>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
"""

from operator import itemgetter

class ClassifyI:

    def train(self, gold_standard):
        """
        @param gold_standard: maps class name to representative samples
        @ret: nothing if successful
        """ 
        raise NotImplementedError() 
 
    def get_class(self, tokens):
        """
        @param tokens: sample to be classified
        @ret: only the most probable class name
        """
        raise NotImplementedError()

    def get_class_list(self, tokens):
        """
        @param tokens: sample to be classified
        @ret: a list of all classes in order of most likely to least likely class
        """
        raise NotImplementedError()

    def get_class_probs(self, tokens):
        """
        @param tokens: sample to be classified
        @ret: DictionaryProbDist of class name and probability
              see nltk.probability.py
        """
        raise NotImplementedError()

    def get_class_tuples(self, tokens):
        """
        @param tokens: sample to be classified
        @ret: dictionary of class names to probability
        """
        raise NotImplementedError()
        
        

class AbstractClassify(ClassifyI):

    def classes():
        """
        @ret: the set of known classes
        """
        return self._classes

    def get_class(self, text):
        """
        @param text: sample to be classified
        @ret: most probable class
        """
        (cls, prob) = self.get_class_tuples(text)[0]
        return cls

    def get_class_list(self, text):
        """
        @param text: sample to be classified 
        @ret: ordered list of classification results
        """
        tuplelist = self.get_class_tuples(text)
        return [cls for (cls,prob) in tuplelist]

    def get_class_tuples(self, text):
        """
        @param text: sample to be classified
        @ret: an ordered list of tuples
        """
        tmp = self.get_class_dict(text)
        return sorted([(cls, tmp[cls]) for cls in tmp],
                      key=itemgetter(1), reverse=True)

    def get_class_probs(self, text):
        """
        @param text: sample to be classified
        @ret: a normalised probability dictionary
        see probability.py
        """
    
        return DictionaryProbDist(self.get_class_dict(text), normalize=True)
    


##//////////////////////////////////////////////////////
##  Helper Functions
##//////////////////////////////////////////////////////


def classifier_accuracy(classifier, gold):
    
    correct = 0
    for cls in gold:
        if classifier.get_class(gold[cls]) == cls:
            correct += 1
    return float(correct) / len(gold)


from cosine import *
from naivebayes import *
from spearman import *
