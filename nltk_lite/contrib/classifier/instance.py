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

from nltk_lite.contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
import item

class Instance:
    def __init__(self):
        self.klass_value, self.attrs, self.classifiedKlass = None, None, None
        
    def is_valid(self, klass, attributes):
        return AssertionError()
    
    def value(self, attribute):
        if attribute.is_continuous():
            return float(self.attrs[attribute.index])
        return self.attrs[attribute.index]
    
    def values(self, attributes):
        _values = []
        for attribute in attributes:
            _values.append(self.attrs[attribute.index])
        return _values

    def discretise(self, discretised_attributes):
        for discretised_attribute in discretised_attributes:
            index = discretised_attribute.index
            self.attrs[index] = discretised_attribute.mapping(float(self.attrs[index]))
    
    def remove_attributes(self, attributes):
        to_be_removed = []
        for attribute in attributes:
            to_be_removed.append(self.attrs[attribute.index])
        for r in to_be_removed:
            self.attrs.remove(r)
    
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
    
    def as_line(self):
        AssertionError()
        
    def attr_values_as_str(self):
        strn = ''
        for attr in self.attrs:
            strn += attr
            strn += ','
        return strn[:-1]
    
class TrainingInstance(Instance):
    def __init__(self, attr_values, klass_value):
        Instance.__init__(self)
        self.klass_value, self.attrs = klass_value, attr_values #values[-1], values[:-1]
        
    def is_valid(self, klass, attributes):
        return klass.__contains__(self.klass_value) and attributes.has_values(self.attrs)
    
    def __str__(self):
        return self.str_attrs() + self.str_class()
    
    def as_line(self):
        return self.attr_values_as_str() + ',' + self.klass_value
        
class TestInstance(Instance):
    def __init__(self, attr_values):
        Instance.__init__(self)
        self.attrs = attr_values#line.split(',')
        
    def set_klass(self, klass):
        self.classifiedKlass = klass
        
    def is_valid(self, klass, attributes):
        return attributes.has_values(self.attrs)
    
    def __str__(self):
        return self.str_attrs() + self.str_klassified_klass()
    
    def as_line(self):
        if self.classifiedKlass == None:
            return self.attr_values_as_str()
        return self.attr_values_as_str() + ',' +self.classifiedKlass
    
class GoldInstance(TrainingInstance, TestInstance):
    def __init__(self, attr_values, klass_value):
        TrainingInstance.__init__(self, attr_values, klass_value)
        
    def is_valid(self, klass, attributes):
        return TrainingInstance.is_valid(self, klass, attributes)
    
    def classificationType(self):
        if self.classifiedKlass == None: raise system.SystemError('Cannot find classification type for instance that has not been classified')
        
    def __str__(self):
        return Instance.__str__(self)
        
    def as_line(self):
        training_as_line = TrainingInstance.as_line(self)
        if self.classifiedKlass == None:
            return training_as_line
        return training_as_line + ',' + self.classifiedKlass
    
class AttributeComparator:
    def __init__(self, attribute):
        self.attribute = attribute
        
    def compare(self, x, y):
        return cmp(x.value(self.attribute), y.value(self.attribute))