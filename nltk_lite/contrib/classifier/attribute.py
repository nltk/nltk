# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier.exceptions import systemerror as se
from nltk_lite.contrib.classifier import autoclass as ac, cfile, decisionstump as ds
import UserList

CONTINUOUS = 'continuous'
DISCRETE = 'discrete'

class Attribute:
    def __init__(self, name, values, index):
        self.name = name
        self.values = values
        self.type = self.__get_type()
        self.index = index
    
    def __get_type(self):
        if len(self.values) == 1 and self.values[0] == CONTINUOUS:
            return CONTINUOUS
        return DISCRETE
        
    def has_value(self, to_test):
        return self.values.__contains__(to_test)
    
    def is_continuous(self):
        return self.type == CONTINUOUS

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.name == other.name and \
           self.values == other.values and \
           self.index == other.index: 
            return True
        return False
    
    def __str__(self):
        return self.name +':' + str(self.values) + ' index:' + str(self.index)
    
    def as_line(self):
        values_str = ''
        for value in self.values:
            values_str += value + ','
        return self.name + ':' + values_str[:-1] + '.'
    
class Attributes(UserList.UserList):
    def __init__(self, attributes = []):
        self.data = attributes

    def has_values(self, test_values):
        if len(test_values) != len(self): return False
        for i in range(len(test_values)):
            test_value = test_values[i]
            if self.data[i].is_continuous(): continue #do not test continuous attributes
            if not self.data[i].has_value(test_value): return False
        return True
    
    def has_continuous_attributes(self):
        for attribute in self.data:
            if attribute.is_continuous(): 
                return True
        return False
    
    def subset(self, indices):
        subset = []
        for index in indices:
            subset.append(self.data[index])
        return subset

    def discretise(self, discretised_attributes):
        for disc_attr in discretised_attributes:
            self.data[disc_attr.index] = disc_attr
            
    def empty_decision_stumps(self, ignore_attributes, klass):
        decision_stumps = []
        for attribute in self.data:
            if attribute in ignore_attributes:
                continue
            decision_stumps.append(ds.DecisionStump(attribute, klass))
        return decision_stumps

    def remove_attributes(self, attributes):
        for attribute in attributes:
            self.remove(attribute)
        #reset indices
        for i in range(len(self.data)):
            self.data[i].index = i

    def write_to_file(self, klass, path, suffix, format):
        _new_file = cfile.File(path + suffix, format.NAMES)
        _new_file.create(True)
        lines = []
        klass_as_line = ''
        for value in klass:
            klass_as_line += str(value) + ','
        lines.append(klass_as_line[:-1] + '.')
        for attribute in self.data:
            lines.append(attribute.as_line())
        _new_file.write(lines)
        return path + suffix + '.' + format.NAMES
