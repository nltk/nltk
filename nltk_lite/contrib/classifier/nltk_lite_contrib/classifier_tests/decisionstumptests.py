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
    
    def testCreatesCountMap(self): 
        self.assertEqual(3, len(self.stump.counts))
        for attr_value in self.attribute.values:
            for class_value in self.klass.values:
                self.assertEqual(0, self.stump.counts[attr_value][class_value])
    
    def testUpdatesCountWithInstanceValues(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.stump.updateCount(instances.instances[0])
        for attr_value in self.attribute.values:
            for class_value in self.klass.values:
                #sunny,hot,high,false,no
                if attr_value == 'sunny' and class_value == 'no': continue
                self.assertEqual(0, self.stump.counts[attr_value][class_value])
        self.assertEqual(1, self.stump.counts['sunny']['no'])

    def testErrorCount(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        for instance in instances.instances:
            self.stump.updateCount(instance)
        self.assertAlmostEqual(0.2222222, self.stump.error())
        self.assertEqual('outlook', self.stump.name)