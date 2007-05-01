# Natural Language Toolkit - Decision Stump
#  Understands the procedure of creating a decision stump and 
#     calculating the number of errors
#  Is generally created at the attribute level
#   ie. each attribute will have a decision stump of its own
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from math import log
from nltk_lite.probability import FreqDist

class DecisionStump:
    def __init__(self, attribute, klass):
        self.attribute = attribute
        """
        counts is a dictionary in which 
        each key is an attribute value
        and each value is a dictionary of class frequencies for that attribute value
        """
        self.counts, self.children = {}, {} #it has children only in decision trees
        self.root = dictionary_of_values(klass)
        for value in attribute.values:
            self.counts[value] = dictionary_of_values(klass)
            
    def update_count(self, instance):
        attr_value = instance.value(self.attribute)
        self.counts[attr_value][instance.klass_value] += 1
        self.root[instance.klass_value] += 1
    
    def error(self):
        count_for_each_attr_value = self.counts.values()
        total, errors = 0, 0
        for class_count in count_for_each_attr_value:
            subtotal, counts = 0, class_count.values()
            counts.sort()
            counts.reverse()
            for count in counts: subtotal += count
            errors += (subtotal - counts[0])
            total += subtotal
        return float(errors)/ total
    
    def klass(self, instance):
        attr_value = instance.value(self.attribute)
        if not self.children.has_key(attr_value):
            return self.majority_klass(attr_value)
        return self.children[attr_value].klass(instance)
    
    def majority_klass(self, attr_value):
        klass_values_with_count = self.counts[attr_value]
        _max, klass_value = 0, None
        for klass, count in klass_values_with_count.items():
            if count > _max:
                _max, klass_value = count, klass
        return klass_value
    
    def entropy(self, attr_value):
        """
        Returns the entropy of class disctribution for a particular attribute value
        """
        from nltk_lite.contrib.classifier import entropy_of_key_counts
        return entropy_of_key_counts(self.counts[attr_value])
    
    def mean_information(self):
        total, total_num_of_instances = 0, 0
        for attr_value in self.attribute.values:
            instance_count = total_counts(self.counts[attr_value])
            if instance_count == 0: 
                continue
            total += (instance_count * self.entropy(attr_value))
            total_num_of_instances += instance_count
        return float(total) / total_num_of_instances
    
    def information_gain(self):
        from nltk_lite.contrib.classifier import entropy_of_key_counts
        return entropy_of_key_counts(self.root) - self.mean_information()
    
    def __str__(self):
        _str = 'Decision stump for attribute ' + self.attribute.name
        for key, value in self.counts.items():
            _str += '\nAttr value: ' + key + '; counts: ' + value.__str__()
        for child in self.children:
            _str += child.__str__()
        return _str
        
def total_counts(dictionary_of_klass_freq):
    total = 0
    for count in dictionary_of_klass_freq.values():
        total += count
    return total    
        
def dictionary_of_values(klass):
    _values = {}
    for value in klass:
        _values[value] = 0
    return _values
