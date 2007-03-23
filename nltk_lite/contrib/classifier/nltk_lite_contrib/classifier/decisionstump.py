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

class DecisionStump:
    def __init__(self, attribute, klass):
        self.counts = {} #, self.max_counts = {}, {}
        self.attribute = attribute
        for value in attribute.values:
            self.counts[value] = klass.dictionary_of_values()
            
    def update_count(self, instance):
        attr_value = instance.value(self.attribute)
        self.counts[attr_value][instance.klass_value] += 1
    
    def error(self):
        class_count_for_each_attribute = self.counts.values()
        total, errors = 0, 0
        for class_count in class_count_for_each_attribute:
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
        max, klass_value = 0, None
        for key, value in klass_values_with_count.items():
            if klass_values_with_count[key] > max:
                max, klass_value = value, key
        return klass_value
    
    def __str__(self):
        str = 'Decision stump for attribute ' + self.attribute.name
        for key, value in self.counts.items():
            str = str + '\nAttr value: ' + key + '; counts: ' + value.__str__()
        return str
        