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
            raise inv.InvalidDataError('Value ' + str(continuous_value) + ' not found in any of the ranges.')
        return self.values[range_index]

def binary_search(ranges, value):
    length = len(ranges)
    mid = length / 2;
    while not ranges[mid].includes(value) and not (mid == 0 or mid == length - 1):
        if ranges[mid].upper < value: # search upper half
            mid = (mid + length) / 2
        else: # search lower half
            mid = mid / 2
    if ranges[mid].includes(value): 
        return mid
    return -1
            
