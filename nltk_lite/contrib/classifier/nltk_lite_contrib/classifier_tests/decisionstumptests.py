# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import decisionstump as ds, attributes as attrs, attribute as attr, klass as k, instances as ins, instance
from nltk_lite_contrib.classifier_tests import *

class DecisionStumpTestCase(unittest.TestCase):
    def setUp(self):
        attributes = attrs.Attributes(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.outlook_attr = attributes[0]
        self.klass = k.Klass(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.outlook_stump = ds.DecisionStump(self.outlook_attr, self.klass)
        self.instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
    
    def test_creates_count_map(self): 
        self.assertEqual(3, len(self.outlook_stump.counts))
        for attr_value in self.outlook_attr.values:
            for class_value in self.klass.values:
                self.assertEqual(0, self.outlook_stump.counts[attr_value][class_value])
    
    def test_updates_count_with_instance_values(self):
        self.outlook_stump.update_count(self.instances.instances[0])
        for attr_value in self.outlook_attr.values:
            for class_value in self.klass.values:
                if attr_value == 'sunny' and class_value == 'no': continue
                self.assertEqual(0, self.outlook_stump.counts[attr_value][class_value])
        self.assertEqual(1, self.outlook_stump.counts['sunny']['no'])

    def test_error_count(self):
        self.__update_stump()
        self.assertAlmostEqual(0.2222222, self.outlook_stump.error())
        self.assertEqual('outlook', self.outlook_stump.attribute.name)
        
    def __update_stump(self):
        for instance in self.instances.instances:
            self.outlook_stump.update_count(instance)
        
    def test_majority_class_for_attr_value(self):
        self.__update_stump()
        self.assertEqual('no', self.outlook_stump.majority_klass_for('sunny'))
        self.assertEqual('yes', self.outlook_stump.majority_klass_for('overcast'))
        self.assertEqual('yes', self.outlook_stump.majority_klass_for('rainy'))
        
    def test_classifies_instance_correctly(self):
        self.__update_stump()
        self.assertEqual('no', self.outlook_stump.klass(instance.GoldInstance('sunny,mild,normal,true,yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.GoldInstance('overcast,mild,normal,true,yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.GoldInstance('rainy,mild,normal,true,yes')))
        self.assertEqual('no', self.outlook_stump.klass(instance.TestInstance('sunny,mild,normal,true,yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.TestInstance('overcast,mild,normal,true,yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.TestInstance('rainy,mild,normal,true,yes')))