# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, instance, klass as k, attributes as attrs
from nltk_lite.contrib.classifier.exceptions import systemerror as system
from nltk_lite.contrib.classifier_tests import *

class InstancesTestCase(unittest.TestCase):
    def test_the_number_of_instances(self):
        instances = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(instances), '7 instances should be present')
        
    def test_validatiy_of_attribute_values(self):
        path = datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes'
        instances = ins.TrainingInstances(path)
        self.assertFalse(instances.are_valid(k.Klass(path), attrs.Attributes(path)))
        
    def test_equality(self):
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
        
    def test_gold_instances_are_created_from_gold_files(self):
        gold = ins.GoldInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(gold))
        self.assertEqual(instance.GoldInstance, gold.instances[0].__class__)

    def test_gold_insts_thrws_system_error_if_confusion_matrix_is_invoked_bfore_classification(self):
        gold = ins.GoldInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        try:
            gold.confusion_matrix(None)
            self.fail('Should throw exception as it is not classified yet')
        except system.SystemError:
            pass

    def test_filtering_does_not_affect_existing_instances(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        training = ins.TrainingInstances(path)
        self.assertEqual(7, len(training))
        attributes = attrs.Attributes(path)
        filtered = training.filter(attributes[1], 'big')
        self.assertEqual(3, len(filtered))
        self.assertEqual(7, len(training))
 
#    def test_naive_unsupervised_discretization(self):
#        training = ins.TrainingInstances()

        
        