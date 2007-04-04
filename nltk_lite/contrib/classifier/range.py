# Natural Language Toolkit - Range
#  Represents a range of numbers, not an immutable object and can be modified by include
#  Capable of performing operations on ranges
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

DELTA = 0.000001

class Range:
    def __init__(self, lower, upper, upper_includes_max=True):
        """
        any number within this range should be greater than or equal to self.lower and 
        less than (or less than equal to depending on whether it includes the max) self.upper
        """
        self.lower = lower
        self.upper = upper
        self.__delta_added = False
        if upper_includes_max:
            self.upper += DELTA
            self.__delta_added = True
    
    def include(self, number):
        if number < self.lower:
            self.lower = number
        elif number > self.upper:
            self.upper = number + DELTA
            self.__delta_added = True
            
    def includes(self, number):
        return self.lower <= number and self.upper > number

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__ : return False
        if self.lower == other.lower and self.upper == other.upper: return True
        return False
    
    def __hash__(self):
        return hash(self.lower) + hash(self.upper)