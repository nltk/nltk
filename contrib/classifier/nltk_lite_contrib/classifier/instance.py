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

from nltk_lite_contrib.classifier.exceptions import systemerror as system
import item

class Instance:
    def __init__(self):
        self.klass_value, self.attrs, self.classifiedKlass = None, None, None
        
    def is_valid(self, klass, attributes):
        return AssertionError()
    
    def value(self, attribute):
        return self.attrs[attribute.index]
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klass_value == other.klass_value and self.attrs == other.attrs and self.classifiedKlass == other.classifiedKlass: return True
        return False
    
    def __str__(self):
        return self.str_attrs() + self.str_class() + self.str_klassified_klass()

    def str_klassified_klass(self):
        return ' Classified as: ' + self.check_none(self.classifiedKlass)

    def check_none(self, var):
        if var is None: 
            return ' '
        return var.__str__()

    def str_class(self):
        return ' Class: ' + self.check_none(self.klass_value)

    def str_attrs(self):
        return 'Attributes: ' + self.check_none(self.attrs)
    
class TrainingInstance(Instance):
    def __init__(self, line):
        Instance.__init__(self)
        values = line.split(',')
        self.klass_value, self.attrs = values[-1], values[:-1]
        
    def is_valid(self, klass, attributes):
        return klass.has_value(self.klass_value) and attributes.has_values(self.attrs)
    
    def __str__(self):
        return self.str_attrs() + self.str_class()
        
class TestInstance(Instance):
    def __init__(self, line):
        Instance.__init__(self)
        self.attrs = line.split(',')
        
    def set_klass(self, klass):
        self.classifiedKlass = klass
        
    def is_valid(self, klass, attributes):
        return attributes.has_values(self.attrs)
    
    def __str__(self):
        return self.str_attrs() + self.str_klassified_klass()
    
class GoldInstance(TrainingInstance, TestInstance):
    def __init__(self, line):
        TrainingInstance.__init__(self, line)
        
    def is_valid(self, klass, attributes):
        return TrainingInstance.is_valid(self, klass, attributes)
    
    def classificationType(self):
        if self.classifiedKlass == None: raise system.SystemError('Cannot find classification type for instance that has not been classified')
        
    def __str__(self):
        return Instance.__str__(self)
        
