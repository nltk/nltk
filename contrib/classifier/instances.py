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
from nltk_lite import probability as prob
import math

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
    
    def supervised_breakpoints(self, attribute):
        self.sort_by(attribute)
        attr_values = self.attribute_values(attribute)
        return SupervisedBreakpoints(self.klass_values(), attr_values)
       
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
        
class SupervisedBreakpoints(UserList.UserList):
    """
    Used to find breakpoints for discretisation
    """
    def __init__(self, klass_values, attr_values):
        UserList.UserList.__init__(self, [])
        self.attr_values = attr_values
        self.klass_values = klass_values
        
    def find_naive(self):
        self.data[:] = self.breakpoints_in_class_membership()
        self.adjust_for_equal_values()
        
    def find_entropy_based(self):
        self.extend(self.find_breakpoint(self.klass_values))
        
    def find_breakpoint(self, klass_values):
        breakpoints = []
        position, entropy = min_entropy(klass_values)
        if entropy == 0: return
        breakpoints.append(breakpoint)
        first, second = klass_values[:position+1], klass_values[position+1:]
        breakpoints.extend(self.find_breakpoint(first))
        breakpoints.extend([position + 1 + x for x in self.find_breakpoints(second)])
        return breakpoints
        
        
    def breakpoints_in_class_membership(self):
        """
        Returns an array of indices where the class membership changes from one value to another
        the indicies will always lie between 0 and one less than number of instance, both inclusive.
        """
        breakpoints= []
        for index in range(len(self.klass_values) - 1):
            if self.klass_values[index] != self.klass_values[index + 1]:
                breakpoints.append(index)
        return breakpoints
    
    def adjust_for_equal_values(self):
        to_be_removed = []
        for index in range(len(self.data)):
            i = index
            while i < len(self.data) - 1 and (self.attr_values[self.data[i]] == self.attr_values[self.data[i] + 1]):
                #The last and second last elements have the same attribute value or is equal to next breakpoint?
                if self.data[i] == len(self.attr_values) - 2 or (index < len(self.data) - 1 and self.data[i] == self.data[index + 1]):
                    to_be_removed.append(self.data[i])
                    break
                self.data[i] += 1
                i += 1
            if index == len(self.data) - 1:#last breakpoint
                breakpoint = self.data[index]
                while breakpoint < len(self.attr_values) - 1 and self.attr_values[breakpoint] == self.attr_values[breakpoint + 1]:
                    self.data[index] += 1
                    if self.data[index] == len(self.attr_values) - 1:
                        to_be_removed.append(self.data[index])
                        break
                    breakpoint = self.data[index]    
        for breakpoint in to_be_removed:
            self.data.remove(breakpoint)
    
    def as_ranges(self):
        ranges, lower = [], self.attr_values[0]
        for breakpoint in self.data:
            mid = (self.attr_values[breakpoint] + self.attr_values[breakpoint + 1]) / 2.0
            ranges.append(r.Range(lower, mid))
            lower = mid
        ranges.append(r.Range(lower, self.attr_values[-1], True))
        return ranges

def min_entropy(values):
    position, min_entropy = 0, None
    for index in range(len(values) -1):
        first, second = values[:index + 1], values[index + 1:]
        e = entropy(first) + entropy(second)
        if min_entropy is None: min_entropy = e
        if e < min_entropy:
            min_entropy = e
            position = index
    return [position, min_entropy]
    
def entropy(values):
    freq_dist = prob.FreqDist()
    for value in values: freq_dist.inc(value)
    sum = 0
    for sample in freq_dist.samples():
        freq = freq_dist.freq(sample)
        sum += (freq * math.log(freq, 2))
    return sum *  -1
