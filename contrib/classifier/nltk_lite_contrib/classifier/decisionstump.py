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
        self.index, self.counts, self.name, self.maxCounts = index, {}, attribute.name, {}
        for value in attribute.values:
            self.counts[value] = klass.valuesWith0Count()
            self.maxCounts[value] = MaxKlassCount(None, 0)
            
    def update_count(self, instance):
        attr_value = instance.valueAt(self.index)
        self.counts[attr_value][instance.klassValue] += 1
        self.maxCounts[attr_value].setHigher(instance.klassValue, self.counts[attr_value][instance.klassValue])
    
    def error(self):
        classCountForEachAttribute = self.counts.values()
        total,errors = 0, 0
        for classCount in classCountForEachAttribute:
            subtotal, counts = 0, classCount.values()
            counts.sort()
            counts.reverse()
            for count in counts: subtotal += count
            errors += (subtotal - counts[0])
            total += subtotal
        return float(errors)/ total
    
    def klass(self, instance):
        return self.maxCounts[instance.valueAt(self.index)].klassValue
        
            
class MaxKlassCount:
    def __init__(self, klassValue, count):
        self.klassValue = klassValue
        self.count = count
        
    def setHigher(self, otherKlassValue, count):
        if otherKlassValue is None: return
        if otherKlassValue is self.klassValue:
            if count > self.count: self.count = count
        else:
            if count > self.count:
                self.count = count
                self.klassValue = otherKlassValue
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.klassValue == other.klassValue and self.count == other.count: return True
        return False
            