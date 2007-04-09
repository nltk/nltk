# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier.exceptions import systemerror as se
from nltk_lite.contrib.classifier import autoclass as ac

CONTINUOUS = 'continuous'
DISCRETE = 'discrete'

class Attribute:
    #line is cleansed of newline, whitespace and dots in attributes
    def __init__(self, line, index):
        self.name = get_name(line)
        self.values = get_values(line)
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
    
def get_name(line):
    return line[:__pos_of_colon(line)]
        
def get_values(line):
    return line[__pos_of_colon(line) + 1:].split(',')
    
def __pos_of_colon(line):
    return line.find(':')
