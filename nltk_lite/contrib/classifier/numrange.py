# Natural Language Toolkit - Range
#  Represents a range of numbers, not an immutable object and can be modified by include
#  Capable of performing operations on ranges
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier.exceptions import systemerror as se
DELTA = 0.000001

class Range:
    def __init__(self, lower = 0, upper = 0, upper_includes_max=False):
        """
        any number within this range should be greater than or equal to self.lower and 
        less than (or less than equal to depending on whether it includes the max) self.upper
        """
        self.__delta_added = False
        if upper < lower: raise se.SystemError('Lower limit cannot be greater than the Upper limit in a range')
        self.__uninitialized = False
        if upper == lower == 0: 
            self.__uninitialized = True
        self.lower, self.upper, self.__delta_added = lower, upper, False
        if upper_includes_max:
            self.upper += DELTA
            self.__delta_added = True
    
    def include(self, number):
        if self.__uninitialized:
            self.lower, self.upper = number, number
            self.__uninitialized = False
        if number >= self.upper:
            self.__delta_added = True
            self.upper = number + DELTA
        elif number < self.lower:
            self.lower = number
            
    def includes(self, number):
        return self.lower <= number and self.upper > number
    
    def split(self, parts):
        if self.lower == self.upper: return None
        len = self.upper - self.lower
        max = self.upper
        if self.__delta_added:
            len -= DELTA
            max -= DELTA
        each = len / parts
        if each < DELTA: return None
        lower, ranges = self.lower, []
        for i in range(parts - 1):
            ranges.append(Range(lower, lower + each))
            lower += each
        ranges.append(Range(lower, self.upper))
        return ranges

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__ : return False
        if self.lower == other.lower and self.upper == other.upper: return True
        return False
    
    def __hash__(self):
        return hash(self.lower) + hash(self.upper)
    
    def __str__(self):
        return '[' + str(self.lower) + ',' + str(self.upper) + ']'