# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier.exceptions import systemerror as se
from nltk_contrib.classifier import autoclass as ac, cfile, decisionstump as ds
from nltk import probability as prob
import UserList

CONTINUOUS = 'continuous'
DISCRETE = 'discrete'

class Attribute:
    """
    Immutable object which represents an attribute/feature
    """
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
        return self.name +':[' + self.values_as_str() + '] index:' + str(self.index)
    
    def values_as_str(self):
        """
        Used to write contents back to file store
        """
        return ','.join([str(value) for value in self.values])
    
    def empty_freq_dists(self):
        return dict([(value, prob.FreqDist()) for value in self.values])
    
    def __hash__(self):
        return hash(self.name) + hash(self.index)        
            
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
    
    def has_continuous(self):
        for attribute in self.data:
            if attribute.is_continuous(): 
                return True
        return False
    
    def subset(self, indices):
        return [self.data[index] for index in indices]

    def discretise(self, discretised_attributes):
        for disc_attr in discretised_attributes:
            self.data[disc_attr.index] = disc_attr
            
    def empty_decision_stumps(self, ignore_attributes, klass):
        filtered = filter(lambda attribute: attribute not in ignore_attributes, self.data)
        return [ds.DecisionStump(attribute, klass) for attribute in filtered]

    def remove_attributes(self, attributes):
        for attribute in attributes:
            self.remove(attribute)
        self.reset_indices()
            
    def reset_indices(self):
        for i in range(len(self.data)):
            self.data[i].index = i
            
    def continuous_attribute_indices(self):
        return [atr.index for atr in self.data if atr.is_continuous()]
    
    def empty_freq_dists(self):
        return dict([(attribute, attribute.empty_freq_dists()) for attribute in self.data])
        
    def __str__(self):
        return '[' + ', '.join([each.__str__() for each in self]) + ']'
            
def fact(n):
    if n==0 or n==1: return 1
    return n * fact(n -1)

def ncr(n, r):
    return fact(n) / (fact(r) * fact(n -r))
