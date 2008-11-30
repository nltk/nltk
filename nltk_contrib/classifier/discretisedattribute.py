# Natural Language Toolkit Discretized attribute
#    Capable of mapping continuous values to discrete ones
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier import attribute, autoclass
from nltk_contrib.classifier.exceptions import invaliddataerror as inv

class DiscretisedAttribute(attribute.Attribute):
    def __init__(self, name, ranges, index):
        self.name = name
        self.values, klass_value = [], autoclass.FIRST
        for i in range(len(ranges)):
            self.values.append(klass_value.name)
            klass_value = klass_value.next()
        self.index = index
        self.type = attribute.DISCRETE
        self.ranges = ranges
        
    def mapping(self, continuous_value):
        range_index = binary_search(self.ranges, continuous_value)
        if range_index == -1: 
            if continuous_value > self.ranges[-1].upper: return self.values[len(self.ranges) - 1]
            else: return self.values[0]
        return self.values[range_index]
    
    def __ranges_as_string(self):
        return str([str(_range) for _range in self.ranges])
    
    def __str__(self):
        return attribute.Attribute.__str__(self) + self.__ranges_as_string()

def binary_search(ranges, value):
    length = len(ranges)
    low, high = 0, length - 1
    mid = low + (high - low) / 2;
    while low <= high:
        if ranges[mid].includes(value):
            return mid
        elif ranges[mid].lower > value: # search lower half
            high = mid - 1
        else: # search upper half
            low = mid + 1
        mid = low + (high - low) / 2
    return -1
            
