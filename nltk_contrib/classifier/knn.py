# Natural Language Toolkit - K nearest neighbour classifier
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, Classifier, distancemetric as dm
from nltk import probability as prob

class IB1(Classifier):
    def __init__(self, training, attributes, klass, internal = False):
        Classifier.__init__(self, training, attributes, klass, internal)
        
    def classify(self, instances):
        for each_test in instances:
            id = InstanceDistances()
            for each_training in self.training:
                dist = dm.euclidean_distance(each_test, each_training, self.attributes)
                id.distance(dist, each_training)
            each_test.set_klass(id.klass(majority_klass_vote))
        
class InstanceDistances:
    """
    Maps instances to the distance they are from a common test_instance
    """
    def __init__(self):
        self.distances = {}
        
    def distance(self, value, instance):
        if self.distances.has_key(value):
            self.distances[value].append(instance)
        else: 
            self.distances[value] = [instance]
            
    def minimum_distance_instances(self):
        keys = self.distances.keys()
        keys.sort()
        return self.distances[keys[0]]
    
    def klass(self, strategy):
        return strategy(self.minimum_distance_instances())
        
def majority_klass_vote(instances):
    fd = prob.FreqDist()
    for each in instances:
        fd.inc(each.klass_value)
    return fd.max()
 