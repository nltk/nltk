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
        
    def test_entropy(self):
        dictionary_of_klass_counts = {}
        dictionary_of_klass_counts['yes'] = 2
        dictionary_of_klass_counts['no'] = 0
        self.assertEqual(0, ds.entropy(dictionary_of_klass_counts))
        
        dictionary_of_klass_counts['yes'] = 3
        dictionary_of_klass_counts['no'] = 3
        self.assertAlmostEqual(1, ds.entropy(dictionary_of_klass_counts))
        
        dictionary_of_klass_counts['yes'] = 9
        dictionary_of_klass_counts['no'] = 5
        self.assertAlmostEqual(0.94, ds.entropy(dictionary_of_klass_counts), 2)
        
        # verify : -(1.0/4 * log(1.0/4, 2)) + -(3.0/4 * log(3.0/4, 2))
        dictionary_of_klass_counts['yes'] = 1
        dictionary_of_klass_counts['no'] = 3
        self.assertAlmostEqual(0.811278, ds.entropy(dictionary_of_klass_counts), 6)

        # verify: -(2.0/3 * log(2.0/3, 2))  + -(1.0/3 * log(1.0/3, 2))
        dictionary_of_klass_counts['yes'] = 2
        dictionary_of_klass_counts['no'] = 1
        self.assertAlmostEqual(0.918296, ds.entropy(dictionary_of_klass_counts), 6)
        
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
    #           = 0.666666              
    def test_mean_information(self):
        self.__update_stump()
        self.assertAlmostEqual(0.6666666, self.outlook_stump.mean_information(), 6)

    # info_gain = entropy(root) - mean_information()
    # entropy(root) = -(5.0/9 * log(5.0/9, 2))  + -(4.0/9 * log(4.0/9, 2)) = 0.99107605983822222
    # mean_info = 0.666666666
    def test_information_gain(self):
        self.__update_stump()
        self.assertAlmostEqual(0.32440939, self.outlook_stump.information_gain(), 6)