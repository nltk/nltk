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
        
    def testUpdatesAMapOfTheMostFrequentlyOccuringClassAtEveryBranchOfTheTree(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['rainy'])
        self.stump.updateCount(instances.instances[0])
        self.assertEqual(ds.MaxKlassCount('no', 1), self.stump.maxCounts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['rainy'])
        self.stump.updateCount(instances.instances[1])
        self.assertEqual(ds.MaxKlassCount('no', 2), self.stump.maxCounts['sunny'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['rainy'])
        self.stump.updateCount(instances.instances[2])
        self.assertEqual(ds.MaxKlassCount('no', 2), self.stump.maxCounts['sunny'])
        self.assertEqual(ds.MaxKlassCount('yes', 1), self.stump.maxCounts['overcast'])
        self.assertEqual(ds.MaxKlassCount(None, 0), self.stump.maxCounts['rainy'])

    def testMaxKlassCountUpdatesWhenItFindsANewClassValueCountHighest(self):
        klassCount = ds.MaxKlassCount(None, 0)
        klassCount.setHigher('yes', 1)
        self.assertEqual('yes', klassCount.klassValue)
        self.assertEqual(1, klassCount.count)

        klassCount.setHigher('yes', 2)        
        self.assertEqual('yes', klassCount.klassValue)
        self.assertEqual(2, klassCount.count)

        klassCount.setHigher('no', 1)        
        self.assertEqual('yes', klassCount.klassValue)
        self.assertEqual(2, klassCount.count)

        klassCount.setHigher('no', 3)        
        self.assertEqual('no', klassCount.klassValue)
        self.assertEqual(3, klassCount.count)
