# Natural Language Toolkit - ZeroR
#  Capable of classifying the test or gold data using the ZeroR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, Classifier

class ZeroR(Classifier):
    def __init__(self, training, attributes, klass):
        Classifier.__init__(self, training, attributes, klass)
        self.__majority_class = None
        self.__klassCount = {}
        
    def train(self):
        Classifier.train(self)
        self.__majority_class = self.majority_class()
        
    def classify(self, instances):
        for instance in instances:
            instance.classified_klass = self.__majority_class
        
    def majority_class(self):
        for instance in self.training:
            self.update_count(instance)
        return self.__max()
    
    def update_count(self, instance):
        klass_value = instance.klass_value
        if klass_value in self.__klassCount:
            self.__klassCount[klass_value] += 1
        else:
            self.__klassCount[klass_value] = 1
            
    def __max(self):
        max, klass_value = 0, None
        for key in self.__klassCount.keys():
            value = self.__klassCount[key]
            if value > max:
                max = value
                klass_value = key
        return klass_value
    
    @classmethod
    def can_handle_continuous_attributes(self):
        return True
    
    def is_trained(self):
        return self.__majority_class is not None
    
