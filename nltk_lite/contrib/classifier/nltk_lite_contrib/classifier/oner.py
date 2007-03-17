# Natural Language Toolkit - OneR
#  Capable of classifying the test or gold data using the OneR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import instances as ins, decisionstump as ds
class OneR:
    def __init__(self, path):
        self.training = OneRTrainingInstances(path)
        if not self.training.areValid(): raise inv.InvalidDataError('Training data invalid')
        self.bestDecisionStump = self.training.bestDecisionStump()
        
    def classify(self, testInstances):
        testInstances.classify(self.bestDecisionStump)


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
                stump.updateCount(instance)
        return self.__minimumError(stumps)
        
    def __minimumError(self, decisionStumps):
        error, min = 1, None
        for decisionStump in decisionStumps:
            e = decisionStump.error()
            if e < error: 
                error = e
                min = decisionStump
        return min

class OneRTestInstances:
    pass