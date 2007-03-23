# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import instances as ins, instance
from nltk_lite_contrib.classifier.exceptions import systemerror as system
from nltk_lite_contrib.classifier_tests import *

class InstancesTestCase(unittest.TestCase):
    def testTheNumberOfInstances(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(instances), '7 instances should be present')
        
    def testValidatiyOfAttributeValues(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertFalse(instances.areValid())
        
    def testEquality(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = ins.TrainingInstances(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertNotEqual(instances, other, 'should not be same')
        
        instances = ins.TestInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = ins.TestInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertNotEqual(instances, other, 'should not be same')
        
    def testGoldInstancesAreCreatedFromGoldFiles(self):
        gold = ins.GoldInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(gold))
        self.assertEqual(instance.GoldInstance, gold.instances[0].__class__)

    def testGoldInstancesThrowSystemExceptionIfConfusionMatrixIsAskedForBeforeClassification(self):
        gold = ins.GoldInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        try:
            gold.confusionMatrix()
            self.fail('Should throw exception as it is not classified yet')
        except system.SystemError:
            pass

        
        