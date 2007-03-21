# Natural Language Toolkit - Instances
#  Understands the creation and validation of instances from input file path
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import klass as k, attributes as attrs, instance as ins, item, file, confusionmatrix as cm
from nltk_lite_contrib.classifier.exceptions import systemerror as system

class Instances:
    def __init__(self, path, suffix):
        self.klass, self.instances = self.createClass(path), []
        self.attributes = attrs.Attributes(path)
        file.File(path, suffix).execute(self, 'createAndAppendInstance')
            
    def createAndAppendInstance(self, l):
        ln = item.Item(l).stripNewLineAndWhitespace()
        if not len(ln) == 0:
            self.instances.append(self.createInstance(ln))
            
    def createClass(self, path):
        return None
        
    def createInstance(self, ln):
        return AssertionError()

    def areValid(self):
        for instance in self.instances:
            if not instance.isValid(self.klass, self.attributes): return False
        return True
    
    def __len__(self):
        return len(self.instances)

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klass == other.klass and \
            self.attributes == other.attributes and \
            self.instances == other.instances:
                return True
        return False

    
class TrainingInstances(Instances):
    def __init__(self, path, ext = file.DATA):
        Instances.__init__(self, path, ext)
        
    def createClass(self, path):
        return k.Klass(path)
    
    def createInstance(self, ln):
        return ins.TrainingInstance(ln)
    
class TestInstances(Instances):
    def __init__(self, path):
        Instances.__init__(self, path, file.TEST)
        
    def createInstance(self, ln):
        return ins.TestInstance(ln)
    
    def print_all(self):
        for instance in self.instances:
            print instance
    
class GoldInstances(TrainingInstances):
    def __init__(self, path):
        TrainingInstances.__init__(self, path, file.GOLD)
        
    def createInstance(self, ln):
        return ins.GoldInstance(ln)
    
    def confusionMatrix(self):
        for i in self.instances:
            if i.classifiedKlass == None: raise system.SystemError('Cannot calculate accuracy as one or more instance(s) are not classified')
        c = cm.ConfusionMatrix(self.klass)
        for i in self.instances:
            c.count(i.klassValue, i.classifiedKlass)
        return c
        
         