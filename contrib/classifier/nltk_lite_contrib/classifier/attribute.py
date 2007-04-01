# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite_contrib.classifier.exceptions import systemerror as se
from nltk_lite_contrib.classifier import nameitem as ni, file

class Attribute:
    #line is cleansed of newline, whitespace and dots in attributes
    def __init__(self, line, index):
        self.name = get_name(line)
        self.values = get_values(line)
        self.index = index
    
    def has_value(self, to_test):
        return self.values.__contains__(to_test)
    
    def unsupervised_equal_width(self, number):
        values = []
        for value in self.values:
            values.append(float(value))
        values.sort()
        first, last = float(values[0]), float(values[len(values) - 1])
        ranges = self.__create_ranges(number, first, last)
        return self.__mapping(ranges, create_values(number))

    def __create_ranges(self, number_of_splits, first, last):
        """
        creates an array of range tuples, where the first element in each tuple 
        is the starting value of the range while the second element is the end 
        value for the range
        A number is in a range if it is greater than or equal to the start value
        and less than the end value
        """
        ranges = []
        value_span = last - first
        width = value_span / number_of_splits
        for index in range(number_of_splits):
            if index == number_of_splits - 1: 
                ranges.append((first, last + 0.000001))
            else:
                ranges.append((first, first + width))
            first = first + width
        return ranges
    
    def __mapping(self, ranges, new_values):
        mapping = {}
        for value in self.values:
            range_index = binary_search(ranges, float(value))
            if range_index == -1: 
                raise se.SystemError('Value ' + value + ' not found in any of the ranges.')
            mapping[float(value)] = new_values[range_index]
        return mapping
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.name == other.name and \
           self.values == other.values and \
           self.index == other.index: 
            return True
        return False
    
def binary_search(ranges, value):
    length = len(ranges)
    mid = length / 2;
    while not (ranges[mid][0] <= value and ranges[mid][1] > value) and not (mid == 0 or mid == length - 1):
        if ranges[mid][1] < value: # search upper half
            mid = (mid + length) / 2
        else: # search lower half
            mid = mid / 2
    if ranges[mid][0] <= value and ranges[mid][1] > value: 
        return mid
    return -1
            
def get_name(line):
    return line[:__pos_of_colon(line)]
        
def get_values(line):
    return line[__pos_of_colon(line) + 1:].split(',')
    
def __pos_of_colon(line):
    return line.find(':')

def create_values(number):
    values = []
    current = 'a'
    for index in range(number):
        values.append(current)
        current = next(current)
    return values

def next(current):
    base26 = __base26(current)
    base26 += 1
    return __string(base26)

def __base26(string):
    base26 = 0
    length = len(string)
    for index in range(length):
        numeric = ord(string[index]) - 97
        if (index == length - 1): base26 += numeric
        else: base26 += numeric * 26 * (length - index - 1)
    return base26

def __string(base26):
    string = ''
    while (base26 /26 > 0):
        string = chr((base26 % 26) + 97) + string
        base26 = base26 / 26
    string = chr((base26 % 26) + 97) + string
    return string