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
        feature_select = fs.FeatureSelect()
        feature_select.parse(['-a', 'RNK', '-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        algorithm = feature_select.values.ensure_value('algorithm', None)
        training = feature_select.values.ensure_value('training', None)
        test = feature_select.values.ensure_value('test', None)
        options = feature_select.values.ensure_value('options', None)
        
        self.assertEqual('RNK', algorithm)
        self.assertEqual('path', training)
        self.assertEqual('path1,path2', test)
        self.assertEqual('IG,4', options)

    def test_validates_algorithm(self):
        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.parse(['-a', 'RNL', '-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        self.assertTrue(feat_sel.error_called)
        self.assertEqual('option -a: invalid choice: \'RNL\' (choose from \'RNK\')', feat_sel.message)

    def test_validates_required_arguments(self):
        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.run(['-a', 'RNK', '-t', 'path', '-o', 'IG,4'])
        self.assertTrue(feat_sel.error_called)
        self.assertEqual('Invalid arguments. One or more required arguments are not present.', feat_sel.message)

        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.run(['-a', 'RNK', '-T', 'path1,path2', '-o', 'IG,4'])
        self.assertTrue(feat_sel.error_called)
        self.assertEqual('Invalid arguments. One or more required arguments are not present.', feat_sel.message)

        #Takes in the default attribute
        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.run(['-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        self.assertFalse(feat_sel.error_called)

        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)    
        try:    
            feat_sel.run(['-a', 'RNK', '-t', 'path', '-T', 'path1,path2'])
        except AttributeError:
            #When not running on the stub will return as soon as it encounters the error
            pass
        self.assertTrue(feat_sel.error_called)
        self.assertEqual('Invalid arguments. One or more required arguments are not present.', feat_sel.message)
        
    def test_cannot_perform_rank_select_on_cont_attrs(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        klass = format.C45_FORMAT.get_klass(path)
        test = format.C45_FORMAT.get_test_instances(path)
        feature_selection = fs.FeatureSelection(training, attributes, klass, test, None, ['IG','2'])
        try:
            feature_selection.by_rank()
            self.fail('should throw error as path points to continuous attributes')
        except inv.InvalidDataError:
            pass
    
    def test_find_attributes_by_ranking(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        klass = format.C45_FORMAT.get_klass(path)
        test = format.C45_FORMAT.get_test_instances(path)
        gold = format.C45_FORMAT.get_gold_instances(path)

        feature_selection = fs.FeatureSelection(training, attributes, klass, test, gold, ['IG','3'])
        
        ig_for_attr1 = information_gain(attributes[0], klass, training)
        self.assertAlmostEqual(0.324409, ig_for_attr1, 6)
        self.assertEqual('outlook', attributes[0].name)
        ig_for_attr2 = information_gain(attributes[1], klass, training)
        self.assertAlmostEqual(0.102187, ig_for_attr2, 6)
        self.assertEqual('temperature', attributes[1].name)
        ig_for_attr3 = information_gain(attributes[2], klass, training)
        self.assertAlmostEqual(0.091091, ig_for_attr3, 6)
        self.assertEqual('humidity', attributes[2].name)
        ig_for_attr4 = information_gain(attributes[3], klass, training)
        self.assertAlmostEqual(0.072780, ig_for_attr4, 6)
        self.assertEqual('windy', attributes[3].name)
        attributes_to_remove = feature_selection.find_attributes_by_ranking('information_gain', 3)
        self.assertEqual(1, len(attributes_to_remove))
        self.assertEqual('windy', attributes_to_remove[0].name)

def information_gain(attribute, klass, instances):
    stump = ds.DecisionStump(attribute, klass)
    for instance in instances:
        stump.update_count(instance)
    return stump.information_gain()

class FeatureSelectStub(fs.FeatureSelect):
    def __init__(self):
        fs.FeatureSelect.__init__(self)
        self.error_called = False
        self.message = None
        
    def error(self, message):
        #in reality error will display usage and quit
        self.message = message
        self.error_called = True
        
    def select_features_and_write_to_file(self):
        pass
