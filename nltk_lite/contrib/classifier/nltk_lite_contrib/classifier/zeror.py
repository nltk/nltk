# Natural Language Toolkit - ZeroR
#  Capable of classifying the test or gold data using the ZeroR algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import exceptions.invaliddataerror as inv
import instances as ins

class ZeroR:
    def __init__(self, path):
        self.training = ZeroRTrainingInstances(path)
        if not self.training.areValid(): raise inv.InvalidDataError('Training data invalid')
        self.majorityClass = None
    
    def classify(self, testInstances):
        if self.majorityClass == None: self.majorityClass = self.training.majorityClass()
        testInstances.setAllClasses(self.majorityClass)
        
    def verify(self, goldInstances):
        self.classify(goldInstances)
        return goldInstances.confusionMatrix()
            
class ZeroRTrainingInstances(ins.TrainingInstances):
    def __init__(self, path):
        ins.TrainingInstances.__init__(self, path)
        self.__klassCount = {}

    def majorityClass(self):
        for instance in self.instances:
            self.__updateCount(instance.klassValue)
        return self.__max()
    
    def __updateCount(self, klassValue):
        if self.__klassCount.has_key(klassValue):
            self.__klassCount[klassValue] += 1
        else:
            self.__klassCount[klassValue] = 1
            
    def __max(self):
        max, klassValue = 0, None
        for key in self.__klassCount.keys():
            value = self.__klassCount[key]
            if value > max:
                max = value
                klassValue = key
        return klassValue
    
class ZeroRTestInstances(ins.TestInstances):
    def __init__(self, path):
        ins.TestInstances.__init__(self, path)
    
    def setAllClasses(self, majorityClass):
        for instance in self.instances:
            instance.setClass(majorityClass)

class ZeroRGoldInstances(ins.GoldInstances, ZeroRTestInstances):
    def __init__(self, path):
        ins.GoldInstances.__init__(self, path)
        
    