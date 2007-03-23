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

class DecisionStump:
    def __init__(self, attribute, klass):
        self.attribute = attribute
        self.counts = {}
        self.root = klass.dictionary_of_values()
        for value in attribute.values:
            self.counts[value] = klass.dictionary_of_values()
            
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
        return self.majority_klass_for(instance.value(self.attribute))
    
    def majority_klass_for(self, attr_value):
        klass_values_with_count = self.counts[attr_value]
        _max, klass_value = 0, None
        for klass, count in klass_values_with_count.items():
            if count > _max:
                _max, klass_value = count, klass
        return klass_value
    
    def mean_information(self):
        total, total_num_of_instances = 0, 0
        for attr_value in self.attribute.values:
            count = self.counts[attr_value]
            instance_count = total_counts(count)
            total += instance_count * entropy(count)
            total_num_of_instances += instance_count
        return float(total) / total_num_of_instances
    
    def __str__(self):
        _str = 'Decision stump for attribute ' + self.attribute.name
        for key, value in self.counts.items():
            _str = _str + '\nAttr value: ' + key + '; counts: ' + value.__str__()
        return _str
        
def total_counts(dictionary_of_klass_counts):
    total = 0
    for count in dictionary_of_klass_counts.values():
        total += count
    return total    
    
def entropy(dictionary_of_klass_counts):
    total, _entropy = 0, 0.0
    for klass, count in dictionary_of_klass_counts.items():
        if count is not 0:
            _entropy = _entropy + (-1 * count * log(count, 2))
            total += count
    _entropy = (_entropy/total) + log(total, 2)
    return _entropy
    