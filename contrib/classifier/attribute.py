# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier.exceptions import systemerror as se
from nltk_lite.contrib.classifier import autoclass as ac, cfile, decisionstump as ds
from nltk_lite import probability as prob
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
    
    def split_info(self):
        from nltk_lite.contrib.classifier import entropy
        return entropy(self.values)

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
    
    def values_as_str(self):
        values_str = ''
        for value in self.values:
            values_str += value + ','
        return values_str[:-1]
    
    def empty_freq_dists(self):
        freq_dists = {}
        for value in self.values:
            freq_dists[value] = prob.FreqDist()
        return freq_dists
    
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
        subset = []
        for index in indices:
            subset.append(self.data[index])
        return subset

    def discretise(self, discretised_attributes):
        for disc_attr in discretised_attributes:
            self.data[disc_attr.index] = disc_attr
            
    def empty_decision_stumps(self, ignore_attributes, klass):
        decision_stumps = []
        filtered = filter(lambda attribute: attribute not in ignore_attributes, self.data)
        for attribute in filtered:
            decision_stumps.append(ds.DecisionStump(attribute, klass))
        return decision_stumps

    def remove_attributes(self, attributes):
        for attribute in attributes:
            self.remove(attribute)
        self.reset_indices()
            
    def reset_indices(self):
        for i in range(len(self.data)):
            self.data[i].index = i
            
    def continuous_attribute_indices(self):
        indices = []
        for atr in self.data:
            if atr.is_continuous(): indices.append(atr.index)
        return indices
    
    def empty_freq_dists(self):
        freq_dists = {}
        for attribute in self.data:
            freq_dists[attribute] = attribute.empty_freq_dists()
        return freq_dists
        
    def __str__(self):
        str = '['
        for each in self:
            str += each.__str__() + ', '
        if len(str) > 1: str = str[:-1]
        return str + ']'
    
            
def fact(n):
    if n==0 or n==1: return 1
    return n * fact(n -1)

def ncr(n, r):
    return fact(n) / (fact(r) * fact(n -r))