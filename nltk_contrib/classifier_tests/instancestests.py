# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, instance, attribute as a, discretisedattribute as da, numrange as nr, util
from nltk_contrib.classifier.exceptions import systemerror as system, invaliddataerror as inv
from nltk_contrib.classifier_tests import *
import math

class InstancesTestCase(unittest.TestCase):
    def test_the_number_of_instances(self):
        instances = ins.TrainingInstances([instance.TrainingInstance(['foo', 'bar'], 'a'), instance.TrainingInstance(['foo', 'foobar'], 'b')])
        self.assertEqual(2, len(instances), '2 instances should be present')
        
    def test_validatiy_of_attribute_values(self):
        path = datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes'
        instances = training(path)
        a, c = metadata(path)
        self.assertFalse(instances.are_valid(c, a))
        
    def test_equality(self):
        instances = training(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = training(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = training(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertNotEqual(instances, other, 'should not be same')
        
        instances = test(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        same = test(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(instances, same, 'should be same')
        other = training(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertNotEqual(instances, other, 'should not be same')
        
    def test_gold_instances_are_created_from_gold_files(self):
        _gold = gold(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(7, len(_gold))
        self.assertEqual(instance.GoldInstance, _gold[0].__class__)

    def test_gold_insts_thrws_system_error_if_confusion_matrix_is_invoked_bfore_classification(self):
        _gold = gold(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        try:
            _gold.confusion_matrix(None)
            self.fail('Should throw exception as it is not classified yet')
        except system.SystemError:
            pass

    def test_filtering_does_not_affect_existing_instances(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        _training = training(path)
        self.assertEqual(7, len(_training))
        _attributes = attributes(path)
        filtered = _training.filter(_attributes[1], 'big')
        self.assertEqual(3, len(filtered))
        self.assertEqual(7, len(_training))

    def test_ranges_of_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        _training = training(path)
        _attributes = attributes(path)
        ranges = _training.value_ranges([_attributes[1]])
        self.assertEqual(1, len(ranges))
        self.assertEqual(6.0, ranges[0].lower)
        self.assertAlmostEqual(33.100001, ranges[0].upper, 6)
        
    def test_ranges_of_multiple_attribute_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        _attributes = attributes(path)
        ranges = _training.value_ranges([_attributes[0], _attributes[1], _attributes[4], _attributes[5], _attributes[6]])
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
        _training = training(path)
        try:
            _training.value_ranges([a.Attribute('outlook', ['sunny','overcast','rainy'], 0)])
            self.fail('should throw error')
        except inv.InvalidDataError:
            pass
        
    def test_discretise_using_discretised_attributes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        _attributes = attributes(path)
        self.assertEqual(0.0, _training[0].value(_attributes[4]))
        self.assertEqual(65000.0, _training[0].value(_attributes[6]))
        disc_dependents = da.DiscretisedAttribute('dependents', nr.Range(0, 2, True).split(2), 4)
        disc_annual_income = da.DiscretisedAttribute('annualincome', nr.Range(0, 120000, True).split(5), 6)
        _training.discretise([disc_dependents, disc_annual_income])
        
        self.assertEqual('a', _training[0].value(disc_dependents))
        self.assertEqual('c', _training[0].value(disc_annual_income))
        
    def test_values_grouped_by_attribute(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        _training = training(path)
        _attributes = attributes(path)
        self.assertEqual([[27.5, 33.1, 32, 18, 12, 10.7, 6, 14.1, 9, 9, 12, 12]] ,_training.values_grouped_by_attribute([_attributes[1]]))
        
    def test_returns_array_of_all_klass_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        klass_values = _training.klass_values()
        
        self.assertEqual(len(_training), len(klass_values))
        for index in range(len(klass_values)):
            self.assertEqual(klass_values[index], _training[index].klass_value)

    def test_sort_by_attribute(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        _attributes = attributes(path)
        attr_values = _training.values_grouped_by_attribute([_attributes[1]])
        self.assertEqual([25.0, 19.0, 21.0, 34.0, 31.0, 42.0], attr_values[0])
        klass_values = _training.klass_values()
        self.assertEqual(['yes', 'no', 'yes', 'yes', 'yes', 'no'], klass_values)
        
        _training.sort_by(_attributes[1])
        attr_values = _training.values_grouped_by_attribute([_attributes[1]])
        self.assertEqual([19.0, 21.0, 25.0, 31.0, 34.0, 42.0], attr_values[0])
        klass_values = _training.klass_values()
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
        _training = training(path)
        _attributes = attributes(path)
        
        breakpoints = _training.supervised_breakpoints(_attributes[1])
        breakpoints.find_naive()
        self.assertEqual(['no', 'yes', 'yes', 'yes', 'yes', 'no'], _training.klass_values())
        self.assertEqual([19.0, 21.0, 25.0, 31.0, 34.0, 42.0], _training.attribute_values(_attributes[1]))
        self.assertEqual(2, len(breakpoints))
        self.assertEqual([0,4], breakpoints)
        
    def test_naive_breakpoints_with_shifting(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _attributes = attributes(path)
        _training = training(path)
        breakpoints = _training.supervised_breakpoints(_attributes[4])
        breakpoints.find_naive()
        
        self.assertEqual(['yes', 'no', 'yes', 'yes', 'yes', 'no'], _training.klass_values())
        self.assertEqual([0.0, 0.0, 0.0, 2.0, 2.0, 2.0], _training.attribute_values(_attributes[4]))
        self.assertEqual(1, len(breakpoints))
        self.assertEqual([2], breakpoints)

    def test_breakpoints_in_class_membership(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no'], [19.0, 21.0, 25.0, 31.0, 34.0, 42.0])
        breakpoints = breakpoints.breakpoints_in_class_membership()
        self.assertEqual(3, len(breakpoints))
        self.assertEqual([0, 1, 4], breakpoints)
    
    def test_entropy_based_breakpoints(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no'], [19.0, 21.0, 25.0, 31.0, 34.0, 42.0])
        breakpoints.find_entropy_based_max_depth(2)
        self.assertEqual(2, len(breakpoints))
        self.assertEqual([4,0], breakpoints.data)
        
    def test_adjust_for_min_freq(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no', 'no', 'yes', 'yes'], [64, 65, 68, 69, 70, 71, 72, 72, 75])
        breakpoints.find_naive()
        self.assertEqual(4, len(breakpoints))
        self.assertEqual([0, 1, 4, 7], breakpoints)
        
        breakpoints.adjust_for_min_freq(4)
        self.assertEqual(1, len(breakpoints))
        self.assertEqual([4], breakpoints)
        
    def test_naive_discretisation_version1(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no', 'no', 'yes', 'yes'], [64, 65, 68, 69, 70, 71, 72, 72, 75])
        breakpoints.find_naive_v1(3)
        self.assertEqual(1, len(breakpoints))
        self.assertEqual([3], breakpoints)
        
    def test_naive_discretisation_version2(self):
        breakpoints = ins.SupervisedBreakpoints(['yes', 'no', 'yes', 'yes', 'yes', 'no', 'no', 'yes', 'yes'], [64, 65, 68, 69, 70, 71, 72, 72, 75])
        breakpoints.find_naive_v2(3)
        self.assertEqual(2, len(breakpoints))
        self.assertEqual([4, 7], breakpoints)

    def test_remove_attributes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _attributes = attributes(path)
        _training = training(path)
        self.assertEqual(8, len(_training[0].attrs))
        self.assertEqual(8, len(_training[-1].attrs))
        _training.remove_attributes([_attributes[0], _attributes[3]])
        self.assertEqual(6, len(_training[0].attrs))
        self.assertEqual(6, len(_training[-1].attrs))

    def test_stratified_bunches(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        self.assertEqual(6, len(_training))
        
        bunches = _training.stratified_bunches(3)
        self.assertEqual(3, len(bunches))
        #training is now sorted.. so content of bunches can be predicted
        self.assertEqual([_training[0], _training[3]], bunches[0])
        self.assertEqual([_training[1], _training[4]], bunches[1])
        self.assertEqual([_training[2], _training[5]], bunches[2])
        
    def test_training_as_gold(self):
        training1 = instance.TrainingInstance(['a','b','c'],'x')
        training2 = instance.TrainingInstance(['d','b','c'],'y')
        training3 = instance.TrainingInstance(['e','b','c'],'z')
        training_instances = [training1, training2, training3]
        gold_instances = ins.training_as_gold(training_instances)
        self.assertEqual(3, len(gold_instances))
        
        for i in [0,1,2]:
            self.assertEqual(training_instances[i].attrs, gold_instances[i].attrs)
            self.assertEqual(training_instances[i].klass_value, gold_instances[i].klass_value)

    def test_training_returns_datasets_for_cross_validation(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        self.assertEqual(6, len(_training))
        datasets = _training.cross_validation_datasets(4)
        
        self.assertEqual(4, len(datasets))
        self.assertEqual(ins.TrainingInstances, datasets[0][0].__class__)
        self.assertEqual(ins.GoldInstances, datasets[0][1].__class__)
        self.assertEqual(4, len(datasets[0][0]))#first training has 4 instances
        self.assertEqual(2, len(datasets[0][1]))#first gold has 2 instances
        self.assertEqual(4, len(datasets[1][0]))#second training has 4 instances
        self.assertEqual(5, len(datasets[2][0]))#third training has 5 instances
        self.assertEqual(5, len(datasets[3][0]))#fourth training has 5 instances
        self.assertEqual(1, len(datasets[3][1]))#fourth gold has 1 instance
        
    def test_cross_validation_datasets_with_fold_greater_than_length_of_training(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        self.assertEqual(6, len(_training))
        datasets = _training.cross_validation_datasets(8)
        
        self.assertEqual(3, len(datasets))
        self.assertEqual(ins.TrainingInstances, datasets[0][0].__class__)
        self.assertEqual(ins.GoldInstances, datasets[0][1].__class__)
        self.assertEqual(4, len(datasets[0][0]))#first training has 4 instances
        self.assertEqual(2, len(datasets[0][1]))#first gold has 2 instances
        self.assertEqual(4, len(datasets[1][0]))#second training has 4 instances
        self.assertEqual(4, len(datasets[2][0]))#third training has 5 instances

    def test_flatten(self):
        result = ins.flatten([[2,3],[4,5],[6,7]])
        self.assertEqual([2,3,4,5,6,7], result)
        
    def test_class_frequency_distribution(self): 
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        class_freq_dist = _training.class_freq_dist()
        self.assertEqual(6, class_freq_dist.N())
        self.assertEqual(2, class_freq_dist.B())
        self.assertEqual(4, class_freq_dist['yes'])
        self.assertEqual(2, class_freq_dist['no'])
        
    def test_class_freq_dist_in_reverse_to_store_classes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        class_freq_dist = _training.class_freq_dist()
        self.assertEqual(['yes','no'], class_freq_dist.keys())
        
        
    def test_posterior_probablities_with_discrete_values(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        _training = training(path)
        _attributes, _klass = metadata(path)
        
        posterior_probabilities = _training.posterior_probablities(_attributes, _klass)
        self.assertAlmostEqual(0.2, posterior_probabilities.value(_attributes[0], 'dual', 'a'))
        self.assertAlmostEqual(0.2, posterior_probabilities.value(_attributes[0], 'dual', 'b'))
        self.assertAlmostEqual(0.6, posterior_probabilities.value(_attributes[0], 'dual', 'c'))
        
        self.assertEqual(len(_attributes), len(posterior_probabilities.freq_dists))
        self.assertEqual(len(_attributes[0].values), len(posterior_probabilities.freq_dists[_attributes[0]]))

    def test_posterior_probabilities_with_cont_values(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _training = training(path)
        _attributes = attributes(path)
        _klass = klass(path)
        
        posterior_probabilities = _training.posterior_probablities(_attributes, _klass)
        #numerical verification
        values_for_class_yes = util.StatList([25,21,34,31])#from data set
        mean = values_for_class_yes.mean()
        sd = values_for_class_yes.std_dev()
        expected_value = (1.0 / math.sqrt(2 * math.pi * sd)) * math.exp(-pow((30 - mean), 2)/ (2 * pow(sd, 2)))
        self.assertEqual(expected_value, posterior_probabilities.value(_attributes[1], 30, 'yes'))
        
        self.assertTrue(posterior_probabilities.value(_attributes[1], 30, 'yes') > posterior_probabilities.value(_attributes[1], 30, 'no'))
        
    def test_prob_using_gaussian_dist(self):
        self.assertAlmostEqual(1.0 / math.sqrt(2 * math.pi), ins.calc_prob_based_on_distrbn(2, 1, 2))
        
    def test_adjust_for_equal_values(self):
        attr_values = [4.2999999999999998, 4.4000000000000004, 4.4000000000000004, 4.4000000000000004, 4.5, 4.5999999999999996, 4.5999999999999996, 4.5999999999999996, 4.5999999999999996, 4.7000000000000002, 4.7000000000000002, 4.7999999999999998, 4.7999999999999998, 4.7999999999999998, 4.7999999999999998, 4.7999999999999998, 4.9000000000000004, 4.9000000000000004, 4.9000000000000004, 4.9000000000000004, 4.9000000000000004, 4.9000000000000004, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.0999999999999996, 5.2000000000000002, 5.2000000000000002, 5.2000000000000002, 5.2000000000000002, 5.2999999999999998, 5.4000000000000004, 5.4000000000000004, 5.4000000000000004, 5.4000000000000004, 5.4000000000000004, 5.4000000000000004, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5999999999999996, 5.5999999999999996, 5.5999999999999996, 5.5999999999999996, 5.5999999999999996, 5.5999999999999996, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7000000000000002, 5.7999999999999998, 5.7999999999999998, 5.7999999999999998, 5.7999999999999998, 5.7999999999999998, 5.7999999999999998, 5.7999999999999998, 5.9000000000000004, 5.9000000000000004, 5.9000000000000004, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0999999999999996, 6.0999999999999996, 6.0999999999999996, 6.0999999999999996, 6.0999999999999996, 6.0999999999999996, 6.2000000000000002, 6.2000000000000002, 6.2000000000000002, 6.2000000000000002, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.2999999999999998, 6.4000000000000004, 6.4000000000000004, 6.4000000000000004, 6.4000000000000004, 6.4000000000000004, 6.4000000000000004, 6.4000000000000004, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5999999999999996, 6.5999999999999996, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7000000000000002, 6.7999999999999998, 6.7999999999999998, 6.7999999999999998, 6.9000000000000004, 6.9000000000000004, 6.9000000000000004, 6.9000000000000004, 7.0, 7.0999999999999996, 7.2000000000000002, 7.2000000000000002, 7.2000000000000002, 7.2999999999999998, 7.4000000000000004, 7.5999999999999996, 7.7000000000000002, 7.7000000000000002, 7.7000000000000002, 7.7000000000000002, 7.9000000000000004]
        klass_values = ['Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-virginica', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-versicolor', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-setosa', 'Iris-setosa', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-setosa', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-versicolor', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica', 'Iris-virginica']
        sb = ins.SupervisedBreakpoints(klass_values, attr_values)
        breakpoints = sb.breakpoints_in_class_membership()
        self.assertEqual([19, 20, 21, 29, 31, 39, 40, 43, 44, 50, 51, 53, 63, 64, 66, 71, 72, 73, 76, 79, 81, 82, 86, 88, 92, 94, 96, 98, 101, 107, 109, 114, 115, 119, 124, 129, 130, 132, 133, 136, 137], breakpoints)
        self.assertAlmostEqual(4.9, attr_values[19])
        self.assertAlmostEqual(4.9, attr_values[20])
        self.assertAlmostEqual(4.9, attr_values[21])
        self.assertAlmostEqual(5.0, attr_values[22])
        self.assertAlmostEqual(5.0, attr_values[29])
        self.assertAlmostEqual(5.0, attr_values[30])
        self.assertAlmostEqual(5.0, attr_values[31])
        self.assertAlmostEqual(5.1, attr_values[32])
        
        sb.find_naive()
        self.assertEqual([21, 31, 40, 44, 51, 58, 64, 72, 79, 82, 88, 94, 98, 107, 114, 119, 129, 132, 136, 137], sb.data)
        self.assertAlmostEqual(4.9, attr_values[sb[0]])
        self.assertAlmostEqual(5.0, attr_values[sb[1]])
        self.assertAlmostEqual(5.1, attr_values[sb[2]])
        
    def test_to_string(self):
        instances = ins.TrainingInstances([instance.TrainingInstance(['foo', 'bar'], 'a'), instance.TrainingInstance(['foo', 'foobar'], 'b')])
        self.assertEqual('[[foo,bar;a], [foo,foobar;b]]', str(instances))

        
if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(InstancesTestCase)))
