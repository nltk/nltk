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
        self.training = OneRTrainingInstances(path)
        if not self.training.areValid(): raise inv.InvalidDataError('Training data invalid')
        self.bestDecisionStump = self.training.bestDecisionStump()
        
    def test(self, path, printResults=True):
        self.testInstances = OneRTestInstances(path)
        self.classify(self.testInstances)
        if printResults: self.testInstances.print_all()
        
    def classify(self, instances):
        instances.classify(self.bestDecisionStump)
        
    def verify(self, path):
        self.goldInstances = OneRGoldInstances(path)
        self.classify(self.goldInstances)
        return self.goldInstances.confusionMatrix()
    
class OneRTrainingInstances(ins.TrainingInstances):
    def __init__(self, path):
        ins.TrainingInstances.__init__(self, path)
            
    def createEmptyDecisionStumps(self):
        decisionStumps,index = [],0
        for attribute in self.attributes:
            decisionStumps.append(ds.DecisionStump(attribute, index, self.klass))
            index+=1
        return decisionStumps
    
    def bestDecisionStump(self):
        stumps = self.createEmptyDecisionStumps();
        for instance in self.instances:
            for stump in stumps:
                stump.update_count(instance)
        return self.__minimumError(stumps)
        
    def __minimumError(self, decisionStumps):
        error, min = 1, None
        for decisionStump in decisionStumps:
            e = decisionStump.error()
            if e < error: 
                error = e
                min = decisionStump
        return min

class OneRTestInstances(ins.TestInstances):
    def __init__(self, path):
        ins.TestInstances.__init__(self, path)
    
    def classify(self, decisionStump):
        for instance in self.instances:
            klass = decisionStump.klass(instance)
            instance.setClass(klass)
            
class OneRGoldInstances(ins.GoldInstances,OneRTestInstances):
    def __init__(self, path):
        ins.GoldInstances.__init__(self, path)
    