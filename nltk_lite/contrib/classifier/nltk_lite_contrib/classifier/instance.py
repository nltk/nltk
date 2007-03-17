# Natural Language Toolkit - Instance
#  Understands the various operations that can be preformed on an instance
#     Each Instance inheriting from the main Instance is capable of operations
#     it can logically perform on that instance value eg: Test instance can 
#     set the Class where as the Training instance cannot
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import item, exceptions.systemerror as system

class Instance:
    def __init__(self):
        self.klassValue, self.attrs, self.classifiedKlass = None, None, None
        
    def isValid(self, klass, attributes):
        return AssertionError()
    
    def valueAt(self, attributeIndex):
        return self.attrs[attributeIndex]
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klassValue == other.klassValue and self.attrs == other.attrs and self.classifiedKlass == other.classifiedKlass: return True
        return False
    
    def __str__(self):
        return 'Attrs: ' + self.attrs.__str__() + ' Class: ' + self.klassValue.__str__() + ' Classified Class: ' + self.classifiedKlass.__str__()
    
class TrainingInstance(Instance):
    def __init__(self, line):
        Instance.__init__(self)
        values = line.split(',')
        self.klassValue, self.attrs = values[-1], values[:-1]
        
    def isValid(self, klass, attributes):
        return klass.hasValue(self.klassValue) and attributes.hasValues(self.attrs)
        
class TestInstance(Instance):
    def __init__(self, line):
        Instance.__init__(self)
        self.attrs = line.split(',')
        
    def setClass(self, klass):
        self.classifiedKlass = klass
        
    def isValid(self, klass, attributes):
        return attributes.hasValues(self.attrs)
    
class GoldInstance(TrainingInstance, TestInstance):
    def __init__(self, line):
        TrainingInstance.__init__(self, line)
        
    def isValid(self, klass, attributes):
        return TrainingInstance.isValid(self, klass, attributes)
    
    def classificationType(self):
        if self.classifiedKlass == None: raise system.SystemError('Cannot find classification type for instance that has not been classified')
        
