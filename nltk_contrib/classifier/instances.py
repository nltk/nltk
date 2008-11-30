# Natural Language Toolkit - Instances
#  Understands the creation and validation of instances from input file path
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instance as ins, item, cfile, confusionmatrix as cm, numrange as r, util
from nltk_contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
from nltk import probability as prob
import operator, UserList, UserDict, math

class Instances(UserList.UserList):
    def __init__(self, instances):
        UserList.UserList.__init__(self, instances)

    def are_valid(self, klass, attributes):
        for instance in self.data:
            if not instance.is_valid(klass, attributes):
                return False
        return True
    
    def discretise(self, discretised_attributes):
        for instance in self.data:
            instance.discretise(discretised_attributes)

    def remove_attributes(self, attributes):
        for instance in self.data:
            instance.remove_attributes(attributes)
            
    def convert_to_float(self, indices):
        for instance in self.data:
            instance.convert_to_float(indices)
            
    def __str__(self):
        return '[' + ', '.join([str(instance) for instance in self.data]) + ']'
            
class TrainingInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
        self.prior_probabilities = None
            
    def filter(self, attribute, attr_value):
        return TrainingInstances([instance for instance in self.data if instance.value(attribute) == attr_value])
    
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
        for value in values: #each entry in values is the range of values for a particular attribute
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
        return [float(value) for value in values]
    
    def klass_values(self):
        return [instance.klass_value for instance in self.data]
    
    def supervised_breakpoints(self, attribute):
        self.sort_by(attribute)
        attr_values = self.attribute_values(attribute)
        return SupervisedBreakpoints(self.klass_values(), attr_values)
       
    def attribute_values(self, attribute):
        return [instance.value(attribute) for instance in self.data]
    
    def sort_by(self, attribute):
        self.data.sort(lambda x, y: cmp(x.value(attribute), y.value(attribute)))
        
    def cross_validation_datasets(self, fold):
        """
        Gold instances are completely new objects except for attribute value objects,
        we wont be changing the attribute value objects in the gold instances anyway 
        unless something really weird is happening!
        """
        if fold > len(self): fold = len(self) / 2
        stratified = self.stratified_bunches(fold)
        datasets = []
        for index in range(len(stratified)):
            gold = GoldInstances(training_as_gold(stratified[index]))
            rest = flatten(stratified[:index]) + flatten(stratified[index + 1:])
            training = TrainingInstances(rest)
            datasets.append((training, gold))
        return datasets
    
    def stratified_bunches(self, fold):
        stratified = [[] for each in range(fold)]
        self.data.sort(key=lambda instance: instance.klass_value)
        for index in range(len(self.data)): stratified[index % fold].append(self.data[index])
        return stratified
    
    def posterior_probablities(self, attributes, klass_values):
        freq_dists = attributes.empty_freq_dists()
        for attribute in attributes:
            for value in attribute.values:
                for klass_value in klass_values:
                    freq_dists[attribute][value].inc(klass_value) #Laplacian smoothing
        stat_list_values = {}
        cont_attrs = filter(lambda attr: attr.is_continuous(), attributes)
        if attributes.has_continuous():
            for attribute in cont_attrs:
                stat_list_values[attribute] = {}
                for klass_value in klass_values:
                    stat_list_values[attribute][klass_value] = util.StatList()
        for instance in self.data:
            for attribute in attributes:
                if attribute.is_continuous():
                    stat_list_values[attribute][instance.klass_value].append(instance.value(attribute))
                else:
                    freq_dists[attribute][instance.value(attribute)].inc(instance.klass_value)
        return PosteriorProbabilities(freq_dists, stat_list_values)
                
    def class_freq_dist(self):
        class_freq_dist = prob.FreqDist()
        for instance in self.data:
            class_freq_dist.inc(instance.klass_value)
        return class_freq_dist
            
#todo remove this      
class TestInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
                    
class GoldInstances(Instances):
    def __init__(self, instances):
        Instances.__init__(self, instances)
            
    def confusion_matrix(self, klass):
        for i in self.data:
            if i.classified_klass == None: 
                raise system.SystemError('Cannot calculate accuracy as one or more instance(s) are not classified')
        matrix = cm.ConfusionMatrix(klass)
        for i in self.data:
            matrix.count(i.klass_value, i.classified_klass)
        return matrix
    
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

    def find_naive_v1(self, min_size):
        frequencies = prob.FreqDist()
        for index in range(len(self.klass_values) - 1):
            frequencies.inc(self.klass_values[index])
            if frequencies[frequencies.max()] >= min_size:
                self.append(index)
                frequencies = prob.FreqDist()
        
    def find_naive_v2(self, min_size):
        self.find_naive()
        self.adjust_for_min_freq(min_size)
        
    def find_entropy_based_max_depth(self, max_depth):
        self.max_depth = max_depth
        self.extend(self.__find_breakpoints(self.klass_values))
        
    def __find_breakpoints(self, klass_values, depth = 0):
        breakpoints = []
        if len(klass_values) <= 1: return breakpoints
        from nltk_contrib.classifier import min_entropy_breakpoint
        position, entropy = min_entropy_breakpoint(klass_values)
        if abs(entropy) == 0: return breakpoints
        breakpoints.append(position)
        first, second = klass_values[:position+1], klass_values[position+1:]
        if depth < self.max_depth:
            breakpoints.extend(self.__find_breakpoints(first, depth + 1))
            breakpoints.extend([position + 1 + x for x in self.__find_breakpoints(second, depth + 1)])
        return breakpoints
    
    def breakpoints_in_class_membership(self):
        """
        Returns an array of indices where the class membership changes from one value to another
        the indicies will always lie between 0 and one less than number of instance, both inclusive.
        """
        return [index for index in range(len(self.klass_values) - 1) if not self.klass_values[index] == self.klass_values[index + 1]]
    
    def adjust_for_min_freq(self, min_size):
        prev = -1
        self.sort()
        to_remove,frequencies = [], prob.FreqDist()
        for breakpoint in self.data:
            frequencies.inc(self.klass_values[breakpoint], breakpoint - prev)
            if frequencies[frequencies.max()] < min_size:
                to_remove.append(breakpoint)
            else:
                frequencies = prob.FreqDist()
            prev = breakpoint    
        for item in to_remove:
            self.remove(item)
    
    def adjust_for_equal_values(self):
        index = 0
        to_be_deleted = []
        while(index < len(self.data) - 1):
            if self.attr_values[self.data[index]] == self.attr_values[self.data[index + 1]]:
                to_be_deleted.append(index)
            else:
                while(self.data[index] < self.data[index + 1] and self.attr_values[self.data[index]] == self.attr_values[self.data[index] + 1]):
                    self.data[index] += 1
            index += 1
        to_be_deleted.sort()
        to_be_deleted.reverse()
        for index in to_be_deleted:
            self.data.__delitem__(index)
        last = self.data[-1]
        while (last < len(self.attr_values) - 1 and self.attr_values[last] == self.attr_values[last + 1]):
            self.data[-1] += 1
            last = self.data[-1]
        if last == len(self.attr_values) - 1: del self.data[-1]
    
    def as_ranges(self):
        ranges, lower = [], self.attr_values[0]
        self.sort()
        for breakpoint in self.data:
            mid = (self.attr_values[breakpoint] + self.attr_values[breakpoint + 1]) / 2.0
            ranges.append(r.Range(lower, mid))
            lower = mid
        ranges.append(r.Range(lower, self.attr_values[-1], True))
        return ranges

class PosteriorProbabilities(UserDict.UserDict):
    def __init__(self, freq_dists, stat_list_values):
        self.freq_dists = freq_dists
        self.stat_list_values = stat_list_values
        
    def value(self, attribute, value, klass_value):
        if attribute.is_continuous():
            stat_list = self.stat_list_values[attribute][klass_value]
            return calc_prob_based_on_distrbn(stat_list.mean(), stat_list.std_dev(), value)
        return self.freq_dists[attribute][value].freq(klass_value)
        
def calc_prob_based_on_distrbn(mean, sd, value):
    if sd == 0: 
        if value == mean:
            return 1
        else: return 0
    return (1.0 / math.sqrt(2 * math.pi * sd)) * math.exp(-pow((value - mean), 2)/ (2 * pow(sd, 2)))
        
def training_as_gold(instances):
    return [instance.as_gold() for instance in instances]

## Utility method
#  needs to be pulled out into a common utility class
def flatten(alist):
    if type(alist) == list:
        elements = []
        for each in alist:
            if type(each) == list:
                elements.extend(flatten(each))
            else:
                elements.append(each)
        return elements
    return None
