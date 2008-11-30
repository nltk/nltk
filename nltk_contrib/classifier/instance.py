# Natural Language Toolkit - Instance
#  Understands the various operations that can be preformed on an instance
#     Each Instance inheriting from the main Instance is capable of operations
#     it can logically perform on that instance value eg: Test instance can 
#     set the Class where as the Training instance cannot
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
import item, copy

class Instance:
    def __init__(self):
        self.klass_value, self.attrs, self.classified_klass = None, None, None
        
    def is_valid(self, klass, attributes):
        """
        Verifies if the instance contains valid attribute and class values
        """
        return attributes.has_values(self.attrs)
    
    def value(self, attribute):
        """
        Returns the value corresponding to @param:attribute
        """
        if attribute.is_continuous():
            return float(self.attrs[attribute.index])
        return self.attrs[attribute.index]
    
    def values(self, attributes):
        """
        Returns a list of attribute values corresponding to @param:attributes
        """
        return [self.attrs[attribute.index] for attribute in attributes]

    def discretise(self, discretised_attributes):
        """
        Set discretised values for continuous attributes
        """
        for discretised_attribute in discretised_attributes:
            index = discretised_attribute.index
            self.attrs[index] = discretised_attribute.mapping(float(self.attrs[index]))
    
    def remove_attributes(self, attributes):
        """
        Used when selecting features and @param:attributes are removed from instances
        @param:attributes is an array of attributes
        """
        to_be_removed = [attribute.index for attribute in attributes]
        to_be_removed.sort()
        to_be_removed.reverse()
        for r in to_be_removed:
            self.attrs.__delitem__(r)
            
    def convert_to_float(self, indices):
        """
        Converts attribute values at @param:indices to floats from numeric data represented as strings
        Will throw a value error if an attempt is made to convert anything other than numeric data
        """
        for index in indices:
            self.attrs[index] = float(self.attrs[index])
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klass_value == other.klass_value and self.attrs == other.attrs and self.classified_klass == other.classified_klass: return True
        return False
    
    def str_klassified_klass(self):
        """
        Returns the classified class as a string, will return <whitespace> if instance is not classified
        """
        return self.__check_none(self.classified_klass)

    def __check_none(self, var):
        if var is None: 
            return ' '
        return var.__str__()

    def str_class(self):
        """
        Returns the class as a string, will return <whitespace> in the case of a test instance
        """
        return self.__check_none(self.klass_value)

    def str_attrs(self):
        """
        Returns the a comma separated string of attribute values
        """
        return ','.join([self.__check_none(each) for each in self.attrs])
    
    def __str__(self):
        return '[' + ';'.join(self.as_str()) + ']'
    
    def as_str(self):
        """
        Helper method for __str__(self)
        """
        return [self.str_attrs()]
        
class TrainingInstance(Instance):
    def __init__(self, attr_values, klass_value):
        Instance.__init__(self)
        self.klass_value, self.attrs = klass_value, attr_values
        
    def is_valid(self, klass, attributes):
        """
        Verifies if the instance contains valid attribute and class values
        """
        return Instance.is_valid(self, klass, attributes) and klass.__contains__(self.klass_value)
    
    def as_gold(self):
        """
        Converts the training instance into a Gold instance(used in cross validation)
        """
        return GoldInstance(copy.copy(self.attrs), self.klass_value)
        
    def as_str(self):
        """
        Helper method for __str__(self)
        """
        _attrs = Instance.as_str(self)
        _attrs.append(self.str_class())
        return _attrs
    
class TestInstance(Instance):
    def __init__(self, attr_values):
        Instance.__init__(self)
        self.attrs = attr_values
        
    def set_klass(self, klass):
        self.classified_klass = klass
        
    def as_str(self):
        """
        Helper method for __str__(self)
        """
        _attrs = Instance.as_str(self)
        _attrs.append(self.str_klassified_klass())
        return _attrs
                
class GoldInstance(TrainingInstance, TestInstance):
    def __init__(self, attr_values, klass_value):
        TrainingInstance.__init__(self, attr_values, klass_value)
        
    def is_valid(self, klass, attributes):
        """
        Verifies if the instance contains valid attribute and class values
        """
        return TrainingInstance.is_valid(self, klass, attributes)
    
    def as_str(self):
        """
        Helper method for __str__(self)
        """
        _attrs = Instance.as_str(self)
        _attrs.append(self.str_class())
        _attrs.append(self.str_klassified_klass())
        return _attrs
    
