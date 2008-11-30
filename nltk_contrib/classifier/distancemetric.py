# Natural Language Toolkit - Distance Metric
#  distance metrics to be used with different types of attributes
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
import math

def euclidean_distance(instance1, instance2, attributes):
    total = 0
    for attribute in attributes:
        d = distance(instance1.value(attribute), instance2.value(attribute), attribute.is_continuous())
        total += d * d
    return math.sqrt(total)
        
def hamiltonian_distance(instance1, instance2, attributes):
    return sum([distance(instance1.value(attribute), instance2.value(attribute), attribute.is_continuous()) for attribute in attributes])

def distance(value1, value2, is_continuous):
    if is_continuous:
        return abs(value1 - value2)    
    if value1 == value2:
        return 0
    return 1
    
    
