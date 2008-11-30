# Natural Language Toolkit - K nearest neighbour classifier
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, Classifier, distancemetric as dm
from nltk import probability as prob

class IB1(Classifier):
    def __init__(self, training, attributes, klass):
        Classifier.__init__(self, training, attributes, klass)
                
    def classify(self, instances):
        for each_test in instances:
            id = InstanceDistances()
            for each_training in self.training:
                dist = dm.euclidean_distance(each_test, each_training, self.attributes)
                id.distance(dist, each_training)
            each_test.classified_klass = id.klass(majority_klass_vote)
    
    @classmethod
    def can_handle_continuous_attributes(self):
        return True
    
    def is_trained(self):
        return True

class InstanceDistances:
    """
    Maps instances to the distance they are from a common test_instance
    """
    def __init__(self):
        self.distances = {}
        
    def distance(self, value, instance):
        if value in self.distances:
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
 
