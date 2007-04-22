# Natural Language Toolkit - Instances
#  Understands the creation and validation of instances from input file path
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instance as ins, item, cfile, confusionmatrix as cm, numrange as r
from nltk_lite.contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
import operator, UserList

class Instances(UserList.UserList):
    def __init__(self, instances):
        UserList.UserList.__init__(self, instances)

    def are_valid(self, klass, attributes):
        for instance in self.data:
            if not instance.is_valid(klass, attributes): 
                return False
        return True
    
    def for_each(self, method):
        for instance in self.data:
            method(instance)
            
    def discretise(self, discretised_attributes):
        for instance in self.data:
            instance.discretise(discretised_attributes)
    
    def write_to_file(self, path, suffix, format):
        _new_file = cfile.File(path + suffix, self.get_extension(format))
        _new_file.create(True)
        lines = []
        for instance in self.data:
            lines.append(instance.as_line())
        _new_file.write(lines)
        return path + suffix + '.' + self.get_extension(format)
    
    def get_extension(self, format):
        return AssertionError()
    
class TrainingInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
            
    def filter(self, attribute, attr_value):
        new_instances = TrainingInstances([])
        for instance in self.data:
            if(instance.value(attribute) == attr_value):
                new_instances.append(instance)
        return new_instances
    
    def value_ranges(self, attributes):
        """
        Returns an array of range objects, in which each corresponds to the range of values an 
        attribute in the attributes parameter can take.
        len(returned range array) is equal to len(attributes)
        """
        ranges = []
        for attribute in attributes:
            if not attribute.is_continuous():
                raise inv.InvalidDataError('Cannot discretise non continuous attribute ' + attribute.name)
        values = self.values_grouped_by_attribute(attributes)
        for index in range(len(attributes)):
            value = values[index]
            value.sort()
            ranges.append(r.Range(value[0], value[-1], True))
        return ranges
    
    def values_grouped_by_attribute(self, attributes):
        """
        Returns an array where each element is an array of attribute values for a particular attribute
        len(returned array) is equal to len(attributes)
        """
        values = []
        for attribute in attributes:
            _vals_in_attr = []
            for instance in self.data:
                if attribute.is_continuous():
                    _vals_in_attr.append(float(instance.value(attribute)))
                else:
                    _vals_in_attr.append(instance.value(attribute))
            values.append(_vals_in_attr)
        return values
        
    def __as_float(self, values):
        floats = []
        for value in values:
            floats.append(float(value))
        return floats
    
    def klass_values(self):
        values = []
        for instance in self.data:
            values.append(instance.klass_value)
        return values
    
    def breakpoints(self, attribute):
        self.sort_by(attribute)
        class_breakpoints = self.breakpoints_in_class_membership()
        attr_values = self.attribute_values(attribute)
        return SupervisedBreakpoints(class_breakpoints, attr_values)
    
    def breakpoints_in_class_membership(self):
        breakpoints, _klass_values = [], self.klass_values()
        for index in range(len(_klass_values) - 1):
            if _klass_values[index] != _klass_values[index + 1]:
                breakpoints.append(index)
        return breakpoints
    
    def attribute_values(self, attribute):
        values = []
        for instance in self.data:
            values.append(instance.value(attribute))
        return values
    
    def sort_by(self, attribute):
        comparator = ins.AttributeComparator(attribute)
        self.data.sort(cmp=comparator.compare)
        
    def get_extension(self, format):
        return format.DATA

class TestInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
        
    def print_all(self):
        for instance in self.data:
            print instance
            
    def get_extension(self, format):
        return format.TEST

class GoldInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
            
    def confusion_matrix(self, klass):
        for i in self.data:
            if i.classifiedKlass == None: 
                raise system.SystemError('Cannot calculate accuracy as one or more instance(s) are not classified')
        matrix = cm.ConfusionMatrix(klass)
        for i in self.data:
            matrix.count(i.klass_value, i.classifiedKlass)
        return matrix
    
    def get_extension(self, format):
        return format.GOLD
        
class SupervisedBreakpoints:
    def __init__(self, class_breakpoints, attr_values):
        self.class_breakpoints = class_breakpoints
        self.attr_values = attr_values
    
    def adjust_for_equal_values(self):
        for index in range(len(self.class_breakpoints)):
            while self.same_values_on_either_side(index) and not self.has_crossed_next_breakpoint(index):
                self.class_breakpoints[index] += 1
            if index != len(self.class_breakpoints) - 1 and self.class_breakpoints[index] >= self.class_breakpoints[index + 1]:
                self.class_breakpoints.remove(self.class_breakpoints[index])
    
    def same_values_on_either_side(self, index):
        breakpoint = self.class_breakpoints[index]
        if breakpoint == len(self.attr_values) - 1:
            return False
        return self.attr_values[breakpoint] == self.attr_values[breakpoint + 1]
    
    def has_crossed_next_breakpoint(self, index):
        """
        Checks if the breakpoint at index is greater than or equal to that at index + 1 for all index 0..len(breakpoints) - 1
        
        consider [2,4,6,8] as the list of breakpoints in class membership
        if the values of a particular attribute are the same on either side of the breakpoint 4 then the breakpoint is 
        moved to a position where the value changes.
        While moving the breakpoint if the new value 6 is greater than or equal to the next breakpoint 6 then, the current 
        breakpoint should be removed, and hence this method checks to see if this condition is true.
        """
        return index == len(self.class_breakpoints) - 1 or self.class_breakpoints[index] >= self.class_breakpoints[index + 1]

    def as_ranges(self):
        ranges, lower = [], self.attr_values[0]
        for breakpoint in self.class_breakpoints:
            mid = (self.attr_values[breakpoint] + self.attr_values[breakpoint + 1]) / 2.0
            ranges.append(r.Range(lower, mid))
            lower = mid
        ranges.append(r.Range(lower, self.attr_values[-1], True))
        return ranges
