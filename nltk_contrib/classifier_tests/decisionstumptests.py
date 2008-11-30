# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import decisionstump as ds, instances as ins, instance
from nltk_contrib.classifier_tests import *
import math

class DecisionStumpTestCase(unittest.TestCase):
    def setUp(self):
        self.attributes, self.klass = metadata(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.outlook_attr = self.attributes[0]
        self.outlook_stump = ds.DecisionStump(self.outlook_attr, self.klass)
        self.instances = training(datasetsDir(self) + 'minigolf' + SEP + 'weather')
    
    def test_creates_count_map(self): 
        self.assertEqual(3, len(self.outlook_stump.counts))
        for attr_value in self.outlook_attr.values:
            for class_value in self.klass:
                self.assertEqual(0, self.outlook_stump.counts[attr_value][class_value])
    
    def test_updates_count_with_instance_values(self):
        self.outlook_stump.update_count(self.instances[0])
        for attr_value in self.outlook_attr.values:
            for class_value in self.klass:
                if attr_value == 'sunny' and class_value == 'no': continue
                self.assertEqual(0, self.outlook_stump.counts[attr_value][class_value])
        self.assertEqual(1, self.outlook_stump.counts['sunny']['no'])

    def test_error_count(self):
        self.__update_stump()
        self.assertAlmostEqual(0.2222222, self.outlook_stump.error())
        self.assertEqual('outlook', self.outlook_stump.attribute.name)
        
    def __update_stump(self):
        for instance in self.instances:
            self.outlook_stump.update_count(instance)
        
    def test_majority_class_for_attr_value(self):
        self.__update_stump()
        self.assertEqual('no', self.outlook_stump.majority_klass('sunny'))
        self.assertEqual('yes', self.outlook_stump.majority_klass('overcast'))
        self.assertEqual('yes', self.outlook_stump.majority_klass('rainy'))
        
    def test_classifies_instance_correctly(self):
        self.__update_stump()
        self.assertEqual('no', self.outlook_stump.klass(instance.GoldInstance(['sunny','mild','normal','true'],'yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.GoldInstance(['overcast','mild','normal','true'],'yes')))
        self.assertEqual('yes', self.outlook_stump.klass(instance.GoldInstance(['rainy','mild','normal','true'],'yes')))
        self.assertEqual('no', self.outlook_stump.klass(instance.TestInstance(['sunny','mild','normal','true'])))
        self.assertEqual('yes', self.outlook_stump.klass(instance.TestInstance(['overcast','mild','normal','true'])))
        self.assertEqual('yes', self.outlook_stump.klass(instance.TestInstance(['rainy','mild','normal','true'])))
        
    def test_total_counts(self):
        dictionary_of_klass_counts = {}
        dictionary_of_klass_counts['yes'] = 2
        dictionary_of_klass_counts['no'] = 0
        self.assertEqual(2, ds.total_counts(dictionary_of_klass_counts))

        dictionary_of_klass_counts['yes'] = 9
        dictionary_of_klass_counts['no'] = 5
        self.assertEqual(14, ds.total_counts(dictionary_of_klass_counts))
        
    # root - yes 5
    #  |     no  4
    #  |
    #  |------sunny----- yes 1
    #  |                 no  3
    #  | 
    #  |------rainy------yes 2
    #  |                 no  1
    #  |
    #  |------overcast---yes 2
    #                    no  0
    #
    # mean info = 4.0/9 * (-(1.0/4 * log(1.0/4, 2)) + -(3.0/4 * log(3.0/4, 2))) + 3.0/9 * (-(2.0/3 * log(2.0/3, 2))  + -(1.0/3 * log(1.0/3, 2))) 
    def test_mean_information(self):
        self.__update_stump()
        expected = 4.0/9 * (-(1.0/4 * math.log(1.0/4, 2)) + -(3.0/4 * math.log(3.0/4, 2))) + 3.0/9 * (-(2.0/3 * math.log(2.0/3, 2))  + -(1.0/3 * math.log(1.0/3, 2))) 
        self.assertAlmostEqual(expected, self.outlook_stump.mean_information(), 6)

    # info_gain = entropy(root) - mean_information()
    # entropy(root) = -(5.0/9 * log(5.0/9, 2))  + -(4.0/9 * log(4.0/9, 2)) = 0.99107605983822222
    # mean_info = 0.666666666
    def test_information_gain(self):
        self.__update_stump()
        entropy = -(5.0/9 * math.log(5.0/9, 2))  + -(4.0/9 * math.log(4.0/9, 2))
        mean_info = 4.0/9 * (-(1.0/4 * math.log(1.0/4, 2)) + -(3.0/4 * math.log(3.0/4, 2))) + 3.0/9 * (-(2.0/3 * math.log(2.0/3, 2))  + -(1.0/3 * math.log(1.0/3, 2))) 
        expected = entropy - mean_info
        self.assertAlmostEqual(expected, self.outlook_stump.information_gain(), 6)
        
    def test_returns_entropy_for_each_attribute_value(self):
        self.__update_stump()

        # there are 4 training instances in all out of which 
        # 3 training instances have their class assigned as no and
        # 1 training instance has its class assigned as yes
        expected = -(1.0/4 * math.log(1.0/4, 2)) + -(3.0/4 * math.log(3.0/4, 2))
        self.assertAlmostEqual(expected, self.outlook_stump.entropy('sunny'), 6)
        
        expected = -(2.0/2 * math.log(2.0/2, 2)) + 0
        self.assertAlmostEqual(0, self.outlook_stump.entropy('overcast'))
        
        expected = -(2.0/3 * math.log(2.0/3, 2)) + -(1.0/3 * math.log(1.0/3, 2))
        self.assertAlmostEqual(expected, self.outlook_stump.entropy('rainy'))
        
    def test_dictionary_of_all_values_with_count_0(self):
        phoney = klass(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        values = ds.dictionary_of_values(phoney);
        self.assertEqual(3, len(values))
        for i in ['a', 'b', 'c']:
            self.assertTrue(values.has_key(i))
            self.assertEqual(0, values[i])
            
    def test_gain_ratio(self):
        self.__update_stump()
        
        entropy = -(5.0/9 * math.log(5.0/9, 2))  + -(4.0/9 * math.log(4.0/9, 2))
        mean_info = 4.0/9 * (-(1.0/4 * math.log(1.0/4, 2)) + -(3.0/4 * math.log(3.0/4, 2))) + 3.0/9 * (-(2.0/3 * math.log(2.0/3, 2))  + -(1.0/3 * math.log(1.0/3, 2))) 
        info_gain = entropy - mean_info
        split_info = -(5.0/12 * math.log(5.0/12, 2)) + -(3.0/12 * math.log(3.0/12, 2))+ -(4.0/12 * math.log(4.0/12, 2))#with smoothing, actual occurances are 4,2,3
        expected = float(info_gain) / split_info
        
        self.assertAlmostEqual(expected, self.outlook_stump.gain_ratio(), 6)
        
    def test_sorting_of_decision_stumps(self):
        stumps = []
        for attribute in self.attributes:
            stumps.append(ds.DecisionStump(attribute, self.klass))
        for instance in self.instances:
            for stump in stumps:
                stump.update_count(instance)
        
        self.assertAlmostEqual(0.324409, stumps[0].information_gain(), 6)
        self.assertAlmostEqual(0.102187, stumps[1].information_gain(), 6)
        self.assertAlmostEqual(0.091091, stumps[2].information_gain(), 6)
        self.assertAlmostEqual(0.072780, stumps[3].information_gain(), 6)

        stumps.sort(lambda x, y: cmp(getattr(x, 'information_gain'), getattr(y, 'information_gain')))

        self.assertAlmostEqual(0.324409, stumps[0].information_gain(), 6)
        self.assertAlmostEqual(0.102187, stumps[1].information_gain(), 6)
        self.assertAlmostEqual(0.091091, stumps[2].information_gain(), 6)
        self.assertAlmostEqual(0.072780, stumps[3].information_gain(), 6)
        
    def test_split_info_with_equal_distribution(self):
        self.outlook_stump.update_count(instance.TrainingInstance(['sunny','mild','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['overcast','mild','normal','true'],'no'))
        self.outlook_stump.update_count(instance.TrainingInstance(['sunny','hot','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['overcast','hot','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','false'],'yes'))
        expected = -(3.0/9 * math.log(3.0/9, 2)) * 3 #3.0/9 and not 2.0/6 because of smoothing
        self.assertEqual(expected, self.outlook_stump.split_info())
        
    def test_split_info_greater_for_higher_arity_attributes(self):
        self.outlook_stump.update_count(instance.TrainingInstance(['sunny','mild','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['overcast','mild','normal','true'],'no'))
        self.outlook_stump.update_count(instance.TrainingInstance(['sunny','hot','normal','false'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['overcast','hot','normal','false'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','true'],'yes'))
        self.outlook_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','false'],'yes'))
        
        windy_stump = ds.DecisionStump(self.attributes[3], self.klass)
        windy_stump.update_count(instance.TrainingInstance(['sunny','mild','normal','true'],'yes'))
        windy_stump.update_count(instance.TrainingInstance(['overcast','mild','normal','true'],'no'))
        windy_stump.update_count(instance.TrainingInstance(['sunny','hot','normal','false'],'yes'))
        windy_stump.update_count(instance.TrainingInstance(['overcast','hot','normal','false'],'yes'))
        windy_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','true'],'yes'))
        windy_stump.update_count(instance.TrainingInstance(['rainy','mild','normal','false'],'yes'))

        self.assertTrue(self.outlook_stump.split_info() > windy_stump.split_info())
