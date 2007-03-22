# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import decisionstump as ds, attributes as attrs, attribute as attr, klass as k, instances as ins
from nltk_lite_contrib.classifier_tests import *

class DecisionStumpTestCase(unittest.TestCase):
    def setUp(self):
        attributes = attrs.Attributes(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.attribute = attributes[0]
        self.klass = k.Klass(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.stump = ds.DecisionStump(self.attribute, 0, self.klass)
    
    def test_creates_count_map(self): 
        self.assertEqual(3, len(self.stump.counts))
        for attr_value in self.attribute.values:
            for class_value in self.klass.values:
                self.assertEqual(0, self.stump.counts[attr_value][class_value])
    
    def test_updates_count_with_instance_values(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.stump.update_count(instances.instances[0])
        for attr_value in self.attribute.values:
            for class_value in self.klass.values:
                #sunny,hot,high,false,no
                if attr_value == 'sunny' and class_value == 'no': continue
                self.assertEqual(0, self.stump.counts[attr_value][class_value])
        self.assertEqual(1, self.stump.counts['sunny']['no'])

    def test_error_count(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        for instance in instances.instances:
            self.stump.update_count(instance)
        self.assertAlmostEqual(0.2222222, self.stump.error())
        self.assertEqual('outlook', self.stump.name)
        
    def test_updates_a_map_of_the_most_frequently_occuring_class_at_every_branch_of_the_tree(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['rainy'])
        self.stump.update_count(instances.instances[0])
        self.assertEqual(ds.MaxKlassCount('no', 1), self.stump.max_counts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['rainy'])
        self.stump.update_count(instances.instances[1])
        self.assertEqual(ds.MaxKlassCount('no', 2), self.stump.max_counts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['rainy'])
        self.stump.update_count(instances.instances[2])
        self.assertEqual(ds.MaxKlassCount('no', 2), self.stump.max_counts['sunny'])
        self.assertEqual(ds.MaxKlassCount('yes', 1), self.stump.max_counts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.max_counts['rainy'])

    def test_max_klass_count_updates_when_it_finds_a_new_class_value_count_highest(self):
        klass_count = ds.MaxKlassCount(None, 0)
        klass_count.set_higher('yes', 1)
        self.assertEqual('yes', klass_count.klass_value)
        self.assertEqual(1, klass_count.count)

        klass_count.set_higher('yes', 2)        
        self.assertEqual('yes', klass_count.klass_value)
        self.assertEqual(2, klass_count.count)

        klass_count.set_higher('no', 1)        
        self.assertEqual('yes', klass_count.klass_value)
        self.assertEqual(2, klass_count.count)

        klass_count.set_higher('no', 3)        
        self.assertEqual('no', klass_count.klass_value)
        self.assertEqual(3, klass_count.count)
