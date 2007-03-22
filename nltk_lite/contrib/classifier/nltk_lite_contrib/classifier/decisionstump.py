# Natural Language Toolkit - Decision Stump
#  Understands the procedure of creating a decision stump and 
#     calculating the number of errors
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

class DecisionStump:
    def __init__(self, attribute, index, klass):
        self.index, self.counts, self.name, self.max_counts = index, {}, attribute.name, {}
        for value in attribute.values:
            self.counts[value] = klass.valuesWith0Count()
            self.max_counts[value] = MaxKlassCount(None, 0)
            
    def update_count(self, instance):
        attr_value = instance.valueAt(self.index)
        self.counts[attr_value][instance.klass_value] += 1
        self.max_counts[attr_value].set_higher(instance.klass_value, self.counts[attr_value][instance.klass_value])
    
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
        return self.max_counts[instance.valueAt(self.index)].klass_value
        
            
class MaxKlassCount:
    def __init__(self, klass_value, count):
        self.klass_value = klass_value
        self.count = count
        
    def set_higher(self, otherKlassValue, count):
        if otherKlassValue is None: return
        if otherKlassValue is self.klass_value:
            if count > self.count: self.count = count
        else:
            if count > self.count:
                self.count = count
                self.klass_value = otherKlassValue
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klass_value == other.klass_value and self.count == other.count: return True
        return False
            