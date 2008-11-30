# Natural Language Toolkit - Distance Metric tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier import distancemetric, instance as ins, attribute as attr
import math

class DistanceMetricTestCase(unittest.TestCase):    
    def test_integer_distance(self):
        self.assertEqual(1, distancemetric.distance(2, 1, True))
        self.assertEqual(1, distancemetric.distance(1, 2, True))
        
    def test_float_distance(self):
        self.assertEqual(0.345, distancemetric.distance(0.968, 0.623, True))
        self.assertEqual(0.345, distancemetric.distance(0.623, 0.968, True))
        
    def test_discrete_distance(self):
        self.assertEqual(1, distancemetric.distance('a', 'b', False))
        self.assertEqual(0, distancemetric.distance('a', 'a', False))
        
    def test_distance_with_one_value_as_string_performs_string_comparison(self):
        self.assertEqual(1, distancemetric.distance('a', 5, False))
        self.assertEqual(1, distancemetric.distance(5, 'b', False))
        
    def test_euclidean_distance(self):
        attributes = [attr.Attribute('A1', ['a','b'], 0), attr.Attribute('A2', ['continuous'], 1), 
                      attr.Attribute('A3', ['continuous'], 2), attr.Attribute('A4', ['g','h'], 3)]
        instance1 = ins.TrainingInstance(['a', 5, 3.4, 'g'], 'y')
        instance2 = ins.TestInstance(['a', 5, 3.4, 'g'])
        self.assertEqual(0, distancemetric.euclidean_distance(instance1, instance2, attributes))
        
        instance2 = ins.TestInstance(['b', 5, 3.4, 'g'])
        self.assertEqual(1, distancemetric.euclidean_distance(instance1, instance2, attributes))

        instance2 = ins.TestInstance(['b', 4, 3.4, 'h'])
        self.assertEqual(math.sqrt(3), distancemetric.euclidean_distance(instance1, instance2, attributes))

        instance2 = ins.TestInstance(['b', 4, 1.4, 'h'])
        self.assertEqual(math.sqrt(7), distancemetric.euclidean_distance(instance1, instance2, attributes))
    
    def test_hamilton_distance(self):
        attributes = [attr.Attribute('A1', ['a','b'], 0), attr.Attribute('A2', ['continuous'], 1), 
                      attr.Attribute('A3', ['continuous'], 2), attr.Attribute('A4', ['g','h'], 3)]
        instance1 = ins.TrainingInstance(['a', 5, 3.4, 'g'], 'y')
        instance2 = ins.TestInstance(['a', 5, 3.4, 'g'])
        self.assertEqual(0, distancemetric.hamiltonian_distance(instance1, instance2, attributes))
        
        instance2 = ins.TestInstance(['b', 5, 3.4, 'g'])
        self.assertEqual(1, distancemetric.hamiltonian_distance(instance1, instance2, attributes))

        instance2 = ins.TestInstance(['b', 4, 3.4, 'h'])
        self.assertEqual(3, distancemetric.hamiltonian_distance(instance1, instance2, attributes))

        instance2 = ins.TestInstance(['b', 4, 1.4, 'h'])
        self.assertEqual(5, distancemetric.hamiltonian_distance(instance1, instance2, attributes))
