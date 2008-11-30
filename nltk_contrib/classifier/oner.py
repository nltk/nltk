# Natural Language Toolkit - OneR
#  Capable of classifying the test or gold data using the OneR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk_contrib.classifier.exceptions import invaliddataerror as inv

class OneR(Classifier):
    
    def __init__(self, training, attributes, klass):
        Classifier.__init__(self, training, attributes, klass)
        self.__best_decision_stump = None
        
    def train(self):
        Classifier.train(self)
        self.__best_decision_stump = self.best_decision_stump(self.training)
        
    def classify(self, instances):
        for instance in instances:
            instance.classified_klass = self.__best_decision_stump.klass(instance)

    def best_decision_stump(self, instances, ignore_attributes = [], algorithm = 'minimum_error'):
        decision_stumps = self.possible_decision_stumps(ignore_attributes, instances)
        try:
            return getattr(self, algorithm)(decision_stumps)
        except AttributeError:
            raise inv.InvalidDataError('Invalid algorithm to find the best decision stump. ' + str(algorithm) + ' is not defined.')
    
    def possible_decision_stumps(self, ignore_attributes, instances):
        """
        Returns a list of decision stumps, one for each attribute ignoring the ones present in the
        ignore list. Each decision stump maintains a count of instances having particular attribute
        values.
        """
        decision_stumps = self.attributes.empty_decision_stumps(ignore_attributes, self.klass);
        for stump in decision_stumps:
            for instance in instances:
                stump.update_count(instance)
        return decision_stumps

        
    def minimum_error(self, decision_stumps):
        """
        Returns the decision stump with minimum error
        """
        error, min_error_stump = 1, None
        for decision_stump in decision_stumps:
            new_error = decision_stump.error()
            if new_error < error: 
                error = new_error
                min_error_stump = decision_stump
        return min_error_stump
    
    def is_trained(self):
        return self.__best_decision_stump is not None
