# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, instance, attribute as a, discretisedattribute as da, numrange as nr, format
from nltk_lite.contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
from nltk_lite.contrib.classifier_tests import *

class InstancesTestCase(unittest.TestCase):
    def test_the_number_of_instances(self):
        instances = ins.TrainingInstances([instance.TrainingInstance(['foo', 'bar'], 'a'), instance.TrainingInstance(['foo', 'foobar'], 'b')])
        self.assertEqual(2, len(instances), '2 instances should be present')
        
    def test_validatiy_of_attribute_values(self):
        path = datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes'
        instances = format.C45_FORMAT.get_training_instances(path)
        klass = format.C45_FORMAT.get_klass(path)
        self.assertFalse(instances.are_valid(klass, format.C45_FORMAT.get_attributes(path)))
        
    def test_equality(self):
        instances = format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertNotEqual(instances, other, 'should not be same')
        
        instances = format.C45_FORMAT.get_test_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = format.C45_FORMAT.get_test_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertNotEqual(instances, other, 'should not be same')
        
    def test_gold_instances_are_created_from_gold_files(self):
        gold = format.C45_FORMAT.get_gold_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(gold))
        self.assertEqual(instance.GoldInstance, gold[0].__class__)

    def test_gold_insts_thrws_system_error_if_confusion_matrix_is_invoked_bfore_classification(self):
        gold = format.C45_FORMAT.get_gold_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        try:
            gold.confusion_matrix(None)
            self.fail('Should throw exception as it is not classified yet')
        except system.SystemError:
            pass

    def test_filtering_does_not_affect_existing_instances(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        training = format.C45_FORMAT.get_training_instances(path)
        self.assertEqual(7, len(training))
        attributes = format.C45_FORMAT.get_attributes(path)
        filtered = training.filter(attributes[1], 'big')
        self.assertEqual(3, len(filtered))
        self.assertEqual(7, len(training))

    def test_ranges_of_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        ranges = training.value_ranges([attributes[1]])
        self.assertEqual(1, len(ranges))
        self.assertEqual(6.0, ranges[0].lower)
        self.assertAlmostEqual(33.100001, ranges[0].upper, 6)
        
    def test_ranges_of_multiple_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        ranges = training.value_ranges([attributes[0], attributes[1], attributes[4], attributes[5], attributes[6]])
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
        training = format.C45_FORMAT.get_training_instances(path)
        try:
            ranges = training.value_ranges([a.Attribute('outlook', ['sunny','overcast','rainy'], 0)]    )
            self.fail('should throw error')
        except inv.InvalidDataError:
            pass
        
    def test_discretise_using_discretised_attributes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        self.assertEqual(0.0, training[0].value(attributes[4]))
        self.assertEqual(65000.0, training[0].value(attributes[6]))
        disc_dependents = da.DiscretisedAttribute('dependents', nr.Range(0, 2, True).split(2), 4)
        disc_annual_income = da.DiscretisedAttribute('annualincome', nr.Range(0, 120000, True).split(5), 6)
        training.discretise([disc_dependents, disc_annual_income])
        
        self.assertEqual('a', training[0].value(disc_dependents))
        self.assertEqual('c', training[0].value(disc_annual_income))
        
    def test_values_grouped_by_attribute(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        self.assertEqual([[27.5, 33.1, 32, 18, 12, 10.7, 6, 14.1, 9, 9, 12, 12]] ,training.values_grouped_by_attribute([attributes[1]]))
        
    def test_returns_array_of_all_klass_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        klass_values = training.klass_values()
        
        self.assertEqual(len(training), len(klass_values))
        for index in range(len(klass_values)):
            self.assertEqual(klass_values[index], training[index].klass_value)

    def test_sort_by_attribute(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        attr_values = training.values_grouped_by_attribute([attributes[1]])
        self.assertEqual([25.0, 19.0, 21.0, 34.0, 31.0, 42.0], attr_values[0])
        klass_values = training.klass_values()
        self.assertEqual(['yes', 'no', 'yes', 'yes', 'yes', 'no'], klass_values)
        
        training.sort_by(attributes[1])
        attr_values = training.values_grouped_by_attribute([attributes[1]])
        self.assertEqual([19.0, 21.0, 25.0, 31.0, 34.0, 42.0], attr_values[0])
        klass_values = training.klass_values()
        self.assertEqual(['no', 'yes', 'yes', 'yes', 'yes', 'no'], klass_values)
        
    def test_ranges_from_breakpoints(self):
        brkpts = ins.SupervisedBreakpoints(['no', 'yes', 'yes', 'yes', 'yes', 'no'], [19.0, 21.0, 25.0, 31.0, 34.0, 42.0])
        brkpts.find_naive()
        ranges = brkpts.as_ranges()
        self.assertEqual(3, len(ranges))
        self.assertEqual(19.0, ranges[0].lower)
        self.assertEqual(20.0, ranges[0].upper)
        self.assertEqual(20.0, ranges[1].lower)
        self.assertEqual(38.0, ranges[1].upper)
        self.assertEqual(38.0, ranges[2].lower)
        self.assertEqual(42.000001, ranges[2].upper)
        
    def test_simple_naive_breakpoints(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        
        breakpoints = training.supervised_breakpoints(attributes[1])
        breakpoints.find_naive()
        self.assertEqual(['no', 'yes', 'yes', 'yes', 'yes', 'no'], training.klass_values())
        self.assertEqual([19.0, 21.0, 25.0, 31.0, 34.0, 42.0], training.attribute_values(attributes[1]))
        self.assertEqual(2, len(breakpoints))
        self.assertEqual([0,4], breakpoints)
        
    def test_naive_breakpoints_with_shifting(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        attributes = format.C45_FORMAT.get_attributes(path)
        training = format.C45_FORMAT.get_training_instances(path)
        breakpoints = training.supervised_breakpoints(attributes[4])
        breakpoints.find_naive()
        
        self.assertEqual(['yes', 'no', 'yes', 'yes', 'yes', 'no'], training.klass_values())
        self.assertEqual([0.0, 0.0, 0.0, 2.0, 2.0, 2.0], training.attribute_values(attributes[4]))
        self.assertEqual(1, len(breakpoints))
        self.assertEqual([2], breakpoints)

    def test_breakpoints_in_class_membership(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no'], [19.0, 21.0, 25.0, 31.0, 34.0, 42.0])

        breakpoints = breakpoints.breakpoints_in_class_membership()
        self.assertEqual(3, len(breakpoints))
        self.assertEqual([0, 1, 4], breakpoints)
        
if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(InstancesTestCase)))
