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
        self.index, self.counts, self.name = index, {}, attribute.name
        for value in attribute.values:
            self.counts[value] = klass.valuesWith0Count()
            
    def updateCount(self, instance):
        self.counts[instance.attrs[self.index]][instance.klassValue] += 1
    
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
        classCounts = self.counts[instance.attrs[index]]
        max, maxClass = 0, None
        classValues = classCounts.keys()
        for classValue in classValues:
            count = classCounts[classValue]
            if count > max:
                max = count
                maxClass = classValue
        return maxClass
                
        
            