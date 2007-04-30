# Natural Language Toolkit - Feature Select tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier import featureselect as fs, decisionstump as ds, format
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

class FeatureSelectTestCase(unittest.TestCase):
    def test_decodes_parameters(self):
        feature_select = fs.FeatureSelectCommandInterface()
        feature_select.parse(['-a', 'RNK', '-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        algorithm = feature_select.values.ensure_value('algorithm', None)
        training = feature_select.values.ensure_value('training', None)
        test = feature_select.values.ensure_value('test', None)
        options = feature_select.values.ensure_value('options', None)
        
        self.assertEqual('RNK', algorithm)
        self.assertEqual('path', training)
        self.assertEqual('path1,path2', test)
        self.assertEqual('IG,4', options)
        
#    TODO
#    def test_validation(self):
#        todo
        
    def test_rank_select_does_not_operate_on_cont_attrs(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        feature_select = fs.FeatureSelect(path, path + '.test', 'IG,2')
        try:
            feature_select.by_rank()
            self.fail('should throw error as path points to continuous attributes')
        except inv.InvalidDataError:
            pass
    
    def test_find_attributes_by_ranking(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        feature_select = fs.FeatureSelect(path, path + '.test,' + path + '.gold', 'IG,2')
        attributes = format.C45_FORMAT.get_attributes(path)
        klass = format.C45_FORMAT.get_klass(path)
        training = format.C45_FORMAT.get_training_instances(path)
        
        ig_for_attr1 = information_gain(attributes[0], klass, training)
        self.assertAlmostEqual(0.324409, ig_for_attr1, 6)
        ig_for_attr2 = information_gain(attributes[1], klass, training)
        self.assertAlmostEqual(0.102187, ig_for_attr2, 6)
        ig_for_attr3 = information_gain(attributes[2], klass, training)
        self.assertAlmostEqual(0.091091, ig_for_attr3, 6)
        ig_for_attr4 = information_gain(attributes[3], klass, training)
        self.assertAlmostEqual(0.072780, ig_for_attr4, 6)
        
        attributes_to_remove = feature_select.find_attributes_by_ranking('information_gain', 3)
        self.assertEqual(1, len(attributes_to_remove))
        self.assertEqual(attributes[3], attributes_to_remove[0])

def information_gain(attribute, klass, instances):
    stump = ds.DecisionStump(attribute, klass)
    instances.for_each(lambda instance: stump.update_count(instance))
    return stump.information_gain()