# Natural Language Toolkit - Instances
#  Understands the creation and validation of instances from input file path
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instance as ins, item, cfile, confusionmatrix as cm, numrange as r
from nltk_lite.contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv

class Instances:
    def __init__(self, path, ext):
        self.path = path
        self.extension = ext
        self.instances = []
        if path is not None:
            cfile.File(path, ext).for_each_line(self.create_and_append_instance)
            
    def create_and_append_instance(self, line):
        _line = item.Item(line).stripNewLineAndWhitespace()
        if not len(_line) == 0:
            self.instances.append(self.create_instance(_line))
            
    def create_instance(self, line):
        return AssertionError()

    def are_valid(self, klass, attributes):
        for instance in self.instances:
            if not instance.is_valid(klass, attributes): 
                return False
        return True
    
    def for_each(self, method):
        for instance in self.instances:
            method(instance)
            
    def discretise(self, discretised_attributes):
        for instance in self.instances:
            instance.discretise(discretised_attributes)
    
    def __getitem__(self, index):
        return self.instances[index]
    
    def __contains__(self, other):
        return self.instances.__contains__(other)
    
    def __len__(self):
        return len(self.instances)

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.instances == other.instances: return True
        return False

    def write_to_file(self, suffix):
        _new_file = cfile.File(self.path + suffix, self.extension)
        _new_file.create(True)
        lines = []
        for instance in self.instances:
            lines.append(instance.as_line())
        _new_file.write(lines)
        return self.path + suffix + '.' + self.extension
    
class TrainingInstances(Instances):
    def __init__(self, path, ext = cfile.DATA):
        Instances.__init__(self, path, ext)
        
    def create_instance(self, line):
        return ins.TrainingInstance(line)
    
    def filter(self, attribute, attr_value):
        new_instances = TrainingInstances(None)
        for instance in self.instances:
            if(instance.value(attribute) == attr_value):
                new_instances.instances.append(instance)
        return new_instances
    
    def as_ranges(self, attributes):
        ranges = []
        for attribute in attributes:
            if not attribute.is_continuous():
                raise inv.InvalidDataError('Cannot discretise non continuous attribute ' + attribute.name)
            ranges.append(r.Range())
        for instance in self.instances:
            values = instance.values(attributes)
            for index in range(len(values)):
                ranges[index].include(float(values[index]))
        return ranges
    
    def values_grouped_by_attribute(self, attributes):
        values = []
        for attribute in attributes:
            _vals_in_attr = []
            for instance in self.instances:
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

class TestInstances(Instances):
    def __init__(self, path):
        Instances.__init__(self, path, cfile.TEST)
        
    def create_instance(self, line):
        return ins.TestInstance(line)
    
    def print_all(self):
        for instance in self.instances:
            print instance

    
class GoldInstances(Instances):
    def __init__(self, path):
        Instances.__init__(self, path, cfile.GOLD)
        
    def create_instance(self, line):
        return ins.GoldInstance(line)
    
    def confusion_matrix(self, klass):
        for i in self.instances:
            if i.classifiedKlass == None: 
                raise system.SystemError('Cannot calculate accuracy as one or more instance(s) are not classified')
        matrix = cm.ConfusionMatrix(klass)
        for i in self.instances:
            matrix.count(i.klass_value, i.classifiedKlass)
        return matrix
        
         