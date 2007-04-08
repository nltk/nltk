# Natural Language Toolkit Discretized attribute
#    Capable of mapping continuous values to discrete ones
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import attribute, autoclass
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

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
            raise inv.InvalidDataError('Value ' + str(continuous_value) + ' of type ' +  str(type(continuous_value)) + ' not found in any of the ranges ' + self.__ranges_as_string())
        return self.values[range_index]
    
    def __ranges_as_string(self):
        str_ranges = []
        for _range in self.ranges:
            str_ranges.append(str(_range))
        return str(str_ranges)
    
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
            
