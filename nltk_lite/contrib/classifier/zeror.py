# Natural Language Toolkit - ZeroR
#  Capable of classifying the test or gold data using the ZeroR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, Classifier

class ZeroR(Classifier):
    def __init__(self, training, attributes, klass, format):
        Classifier.__init__(self, training, attributes, klass, format)
        self.__majority_class = None
        self.__klassCount = {}
        
    def test(self, test_instances, printResults=True):
        self.test_instances = test_instances
        self.classify(self.test_instances)
        if printResults: self.test_instances.print_all()
    
    def classify(self, instances):
        if self.__majority_class == None: 
            self.__majority_class = self.majority_class()
        instances.for_each(self.set_majority_klass)
        
    def verify(self, gold_instances):
        self.gold_instances = gold_instances
        self.classify(self.gold_instances)
        return self.gold_instances.confusion_matrix(self.klass)

    def majority_class(self):
        self.training.for_each(self.update_count)
        return self.__max()
    
    def update_count(self, instance):
        klass_value = instance.klass_value
        if self.__klassCount.has_key(klass_value):
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
    
    def set_majority_klass(self, instance):
        instance.set_klass(self.__majority_class)

    def can_handle_continuous_attributes(self):
        return True
    