# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import knn, instance as ins, instances as inss
from nltk_contrib.classifier_tests import *
import unittest

class KNNTestCase(unittest.TestCase):
    def setUp(self):
        self.ins1 = ins.TrainingInstance(['bar','two'],'a')
        self.ins2 = ins.TrainingInstance(['foo','two'],'a')
        self.ins3 = ins.TrainingInstance(['baz','three'],'b')        
    
    def test_majority_klass_vote_with_no_training_instances(self):
        self.assertEqual(None, knn.majority_klass_vote([]))

    def test_majority_klass_vote_with_training_instances(self):
        self.assertEqual('a', knn.majority_klass_vote([self.ins1, self.ins2, self.ins3]))

    def setup_instance_distances_with_6_instances(self):
        ins4 = ins.TrainingInstance(['bar','one'],'a')
        ins5 = ins.TrainingInstance(['foo','one'],'a')
        ins6 = ins.TrainingInstance(['baz','four'],'b')

        id = knn.InstanceDistances()
        id.distance(1.0, self.ins1)
        id.distance(1.0, self.ins2)
        id.distance(1.0, self.ins3)
        id.distance(2.0, ins4)
        id.distance(3.0, ins5)
        id.distance(2.0, ins6)
        
        return id
    
    def test_instance_distances_min_dist_instances(self):
        id = self.setup_instance_distances_with_6_instances()
        self.assertEqual([self.ins1, self.ins2, self.ins3], id.minimum_distance_instances())
        
    def test_instance_distances_invokes_strategy_with_instances(self):
        id = self.setup_instance_distances_with_6_instances()
        self.assertEqual('foo', id.klass(self.stub_strategy))
    
    def stub_strategy(self, test_parameters):
        self.assertEqual(3, len(test_parameters))
        return 'foo'
        
    def test_ib1(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        _training = training(path)
        _attributes, _klass = metadata(path)
        
        classifier = knn.IB1(_training, _attributes, _klass)
        test_instance = ins.TestInstance(['sunny','hot','high','false'])
        classifier.test(inss.TestInstances([test_instance]))
        self.assertEqual('no', test_instance.classified_klass)
        
