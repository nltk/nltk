# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import re

class Attribute:
    #line is cleansed of newline, whitespace and dots in attributes
    def __init__(self, line):
        self.name = self.__getName(line)
        self.values = self.__getValues(line)

    def __getName(self, line):
        return line[:self.__posOfColon(line)]
    
    def __posOfColon(self, line):
        return re.compile(':').search(line).start()
    
    def __getValues(self, line):
        return line[self.__posOfColon(line) + 1:].split(',')
    
    def hasValue(self, toTest):
        return self.values.__contains__(toTest)
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.name == other.name and self.values == other.values: return True
        return False