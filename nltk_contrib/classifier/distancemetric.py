# Natural Language Toolkit - Distance Metric
#  distance metrics to be used with different types of attributes
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
import math

def euclidean_distance(instance1, instance2, attributes):
    total = 0
    for attribute in attributes:
        d = distance(instance1.value(attribute), instance2.value(attribute))
        total += d * d
    return math.sqrt(total)
        
def hamiltonian_distance(instance1, instance2, attributes):
    total = 0
    for attribute in attributes:
        d = distance(instance1.value(attribute), instance2.value(attribute))
        total += d
    return total

def distance(value1, value2):
    if type(value1) is str or type(value2) is str:
        if value1 is value2:
            return 0
        else: return 1
    return abs(value1 - value2)
    
