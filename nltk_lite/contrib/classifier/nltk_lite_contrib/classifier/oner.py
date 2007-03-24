# Natural Language Toolkit - OneR
#  Capable of classifying the test or gold data using the OneR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import instances as ins, decisionstump as ds, Classifier

class OneR(Classifier):
    def __init__(self, path):
        Classifier.__init__(self, OneRTrainingInstances(path))
        self.best_decision_stump = self.training.best_decision_stump()
        
    def test(self, path, printResults=True):
        self.test_instances = OneRTestInstances(path)
        self.classify(self.test_instances)
        if printResults: self.test_instances.print_all()
        
    def classify(self, instances):
        instances.classify(self.best_decision_stump)
        
    def verify(self, path):
        self.gold_instances = OneRGoldInstances(path)
        self.classify(self.gold_instances)
        return self.gold_instances.confusionMatrix()
    
class OneRTrainingInstances(ins.TrainingInstances):
    def __init__(self, path):
        ins.TrainingInstances.__init__(self, path)
            
    def create_empty_decision_stumps(self, ignore_attributes = []):
        decision_stumps = []
        for attribute in self.attributes:
            if attribute in ignore_attributes:
                continue
            decision_stumps.append(ds.DecisionStump(attribute, self.klass))
        return decision_stumps
    
    def best_decision_stump(self, ignore_attributes = [], algorithm = 'minimum_error'):
        stumps = self.create_empty_decision_stumps(ignore_attributes);
        for instance in self.instances:
            for stump in stumps:
                stump.update_count(instance)
        return getattr(self, algorithm)(stumps)
        
    def minimum_error(self, decision_stumps):
        error, min_error_stump = 1, None
        for decision_stump in decision_stumps:
            new_error = decision_stump.error()
            if new_error < error: 
                error = new_error
                min_error_stump = decision_stump
        return min_error_stump

class OneRTestInstances(ins.TestInstances):
    def __init__(self, path):
        ins.TestInstances.__init__(self, path)
    
    def classify(self, decision_stump):
        for instance in self.instances:
            klass = decision_stump.klass(instance)
            instance.set_klass(klass)
            
class OneRGoldInstances(ins.GoldInstances,OneRTestInstances):
    def __init__(self, path):
        ins.GoldInstances.__init__(self, path)
    