# Natural Language Toolkit - Decision Stump
#  Understands the procedure of creating a decision stump and 
#     calculating the number of errors
#  Is generally created at the attribute level
#   ie. each attribute will have a decision stump of its own
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from math import log
from nltk.probability import FreqDist

class DecisionStump:
    """
    Decision Stump is a tree created for each attribute, with branches for
    each attribute value. It also stores the count for each attribute value
    """
    def __init__(self, attribute, klass):
        self.attribute = attribute
        self.__safe_default = None
        """
        counts is a dictionary in which 
        each key is an attribute value
        and each value is a dictionary of class frequencies for that attribute value
        """
        self.children = {} #it has children only in decision trees
        self.root = dictionary_of_values(klass)
        self.counts = {}
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
            for count in counts: subtotal += count
            errors += (subtotal - counts[-1])
            total += subtotal
        return float(errors)/ total
    
    def klass(self, instance):
        attr_value = instance.value(self.attribute)
        if len(self.children) == 0 or not attr_value in self.children: 
            return self.majority_klass(attr_value)
        return self.children[attr_value].klass(instance)
    
    def majority_klass(self, attr_value):
        klass_values_with_count = self.counts[attr_value]
        _max, klass_value = 0, self.safe_default() # will consider safe default because at times the test will have an attribute value not present in the stump(can happen in cross validation as well)
        for klass, count in klass_values_with_count.items():
            if count > _max:
                _max, klass_value = count, klass
        return klass_value
    
    def safe_default(self):
        """
        Mimics Zero-R behavior by find the majority class in all the occurances at this stump level
        """
        if self.__safe_default == None:
            max_occurance, klass = -1, None
            for klass_element in self.root.keys():
                if self.root[klass_element] > max_occurance:
                    max_occurance = self.root[klass_element]
                    klass = klass_element
            self.__safe_default = klass
        return self.__safe_default
    
    def entropy(self, attr_value):
        """
        Returns the entropy of class disctribution for a particular attribute value
        """
        from nltk_contrib.classifier import entropy_of_key_counts
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
        from nltk_contrib.classifier import entropy_of_key_counts
        return entropy_of_key_counts(self.root) - self.mean_information()
    
    def gain_ratio(self):
        return float(self.information_gain()) / self.split_info()
    
    def split_info(self):
        instance_distrbn = FreqDist()
        for attribute_value in self.counts:
            instance_distrbn.inc(attribute_value)#laplacian smoothing
            class_values = self.counts[attribute_value]
            for class_value in class_values:
                instance_distrbn.inc(attribute_value, self.counts[attribute_value][class_value])
        from nltk_contrib.classifier import entropy_of_freq_dist
        return entropy_of_freq_dist(instance_distrbn)
    
    def __str__(self):
        _str = 'Decision stump for attribute ' + self.attribute.name
        for key, value in self.counts.items():
            _str += '\nAttr value: ' + key + '; counts: ' + value.__str__()
        for child in self.children:
            _str += child.__str__()
        return _str
        
def total_counts(dictionary_of_klass_freq):
    return sum([count for count in dictionary_of_klass_freq.values()])
        
def dictionary_of_values(klass):
    return dict([(value, 0) for value in klass])
