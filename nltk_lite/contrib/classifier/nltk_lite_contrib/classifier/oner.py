# Natural Language Toolkit - OneR
#  Capable of classifying the test or gold data using the OneR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk_lite_contrib.classifier.exceptions import invaliddataerror as inv

class OneR(Classifier):
    def __init__(self, path):
        Classifier.__init__(self, path)
        self.__best_decision_stump = None
        
    def test(self, path, printResults=True):
        self.test_instances = ins.TestInstances(path)
        self.classify(self.test_instances)
        if printResults: self.test_instances.print_all()
        
    def classify(self, instances):
        if self.__best_decision_stump == None:
            self.__best_decision_stump = self.best_decision_stump(self.training)
        instances.for_each(self.set_klass_on_test_or_gold)
        
    def set_klass_on_test_or_gold(self, instance):
        klass = self.__best_decision_stump.klass(instance)
        instance.set_klass(klass)
        
    def verify(self, path):
        self.gold_instances = ins.GoldInstances(path)
        self.classify(self.gold_instances)
        return self.gold_instances.confusion_matrix(self.klass)

    def create_empty_decision_stumps(self, ignore_attributes):
        self.decision_stumps = []
        for attribute in self.attributes:
            if attribute in ignore_attributes:
                continue
            self.decision_stumps.append(ds.DecisionStump(attribute, self.klass))
            
    def best_decision_stump(self, instances, ignore_attributes = [], algorithm = 'minimum_error'):
        self.create_empty_decision_stumps(ignore_attributes);
        instances.for_each(self.update_count_in_decision_stumps)
        try:
            return getattr(self, algorithm)()
        except AttributeError:
            raise inv.InvalidDataError('Invalid algorithm to find the best decision stump. ' + str(algorithm) + ' is not defined.')
        
    def update_count_in_decision_stumps(self, instance):
        for stump in self.decision_stumps:
            stump.update_count(instance)

    def minimum_error(self):
        error, min_error_stump = 1, None
        for decision_stump in self.decision_stumps:
            new_error = decision_stump.error()
            if new_error < error: 
                error = new_error
                min_error_stump = decision_stump
        return min_error_stump