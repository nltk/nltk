# Natural Language Toolkit - OneR
#  Capable of classifying the test or gold data using the OneR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

class OneR(Classifier):
    def __init__(self, training, attributes, klass, internal = False):
        Classifier.__init__(self, training, attributes, klass, internal)
        self.__best_decision_stump = None
        
    def classify(self, instances):
        if self.__best_decision_stump == None:
            self.__best_decision_stump = self.best_decision_stump(self.training)
        for instance in instances:
            klass = self.__best_decision_stump.klass(instance)
            instance.set_klass(klass)

    def best_decision_stump(self, instances, ignore_attributes = [], algorithm = 'minimum_error'):
        self.decision_stumps = self.attributes.empty_decision_stumps(ignore_attributes, self.klass);
        for stump in self.decision_stumps:
            for instance in instances:
                stump.update_count(instance)
        try:
            return getattr(self, algorithm)()
        except AttributeError:
            raise inv.InvalidDataError('Invalid algorithm to find the best decision stump. ' + str(algorithm) + ' is not defined.')
        
    def minimum_error(self):
        error, min_error_stump = 1, None
        for decision_stump in self.decision_stumps:
            new_error = decision_stump.error()
            if new_error < error: 
                error = new_error
                min_error_stump = decision_stump
        return min_error_stump