# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, instance, klass as k, attributes as attrs
from nltk_lite.contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
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

    def test_ranges_of_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        training = ins.TrainingInstances(path)
        attributes = attrs.Attributes(path)
        ranges = training.as_ranges([attributes[1]])
        self.assertEqual(1, len(ranges))
        self.assertEqual(6.0, ranges[0].lower)
        self.assertAlmostEqual(33.100001, ranges[0].upper, 6)
        
    def test_ranges_of_multiple_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = ins.TrainingInstances(path)
        attributes = attrs.Attributes(path)
        ranges = training.as_ranges([attributes[0], attributes[1], attributes[4], attributes[5], attributes[6]])
        self.assertEqual(5, len(ranges))
        self.assertEqual(0, ranges[0].lower)
        self.assertAlmostEqual(5.000001, ranges[0].upper)
        self.assertEqual(19, ranges[1].lower)
        self.assertAlmostEqual(42.000001, ranges[1].upper)
        self.assertEqual(0, ranges[2].lower)
        self.assertAlmostEqual(2.000001, ranges[2].upper)
        self.assertEqual(0, ranges[3].lower)
        self.assertAlmostEqual(6.000001, ranges[3].upper)
        self.assertEqual(0, ranges[4].lower)
        self.assertAlmostEqual(120000.000001, ranges[4].upper)

    def test_attempt_to_discretise_non_continuous_attribute_raises_error(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        training = ins.TrainingInstances(path)
        attributes = attrs.Attributes(path)
        try:
            ranges = training.as_ranges([attributes[0]])
            self.fail('should throw error')
        except inv.InvalidDataError:
            pass
        

        
        
#    def test_naive_unsupervised_discretization(self):
#        training = ins.TrainingInstances()

        
        