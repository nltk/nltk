# Natural Language Toolkit - Feature Select tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier import featureselect as fs, decisionstump as ds, attribute as attr
from nltk_contrib.classifier.exceptions import invaliddataerror as inv
import copy

class FeatureSelectTestCase(unittest.TestCase):
    def test_decodes_parameters(self):
        feature_select = fs.FeatureSelect()
        feature_select.parse(['-a', 'RNK', '-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        algorithm = feature_select.values.ensure_value('algorithm', None)
        _training = feature_select.values.ensure_value('training', None)
        _test = feature_select.values.ensure_value('test', None)
        options = feature_select.values.ensure_value('options', None)
        
        self.assertEqual('RNK', algorithm)
        self.assertEqual('path', _training)
        self.assertEqual('path1,path2', _test)
        self.assertEqual('IG,4', options)

    def test_validates_algorithm(self):
        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.parse(['-a', 'RNL', '-t', 'path', '-T', 'path1,path2', '-o', 'IG,4'])
        self.assertTrue(feat_sel.error_called)
        self.assertEqual('option -a: invalid choice: \'RNL\' (choose from \'RNK\', \'BE\', \'FS\')', feat_sel.message)

    def test_validates_required_arguments(self):
        feat_sel = FeatureSelectStub()
        self.assertFalse(feat_sel.error_called)        
        feat_sel.run(['-a', 'RNK', '-t', 'path', '-o', 'IG,4'])
        self.assertFalse(feat_sel.error_called) # should not throw error this situation can exist if there is only one dataset

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
        _training = training(path)
        attributes, klass = metadata(path)
        _test = test(path)
        feature_selection = fs.FeatureSelection(_training, attributes, klass, _test, None, ['IG','2'])
        try:
            feature_selection.by_rank()
            self.fail('should throw error as path points to continuous attributes')
        except inv.InvalidDataError:
            pass
    
    def test_find_attributes_by_ranking(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        _training = training(path)
        attributes, klass = metadata(path)
        _test = test(path)
        _gold = gold(path)

        feature_selection = fs.FeatureSelection(_training, attributes, klass, _test, _gold, ['IG','3'])
        
        ig_for_attr1 = information_gain(attributes[0], klass, _training)
        self.assertAlmostEqual(0.324409, ig_for_attr1, 6)
        self.assertEqual('outlook', attributes[0].name)
        ig_for_attr2 = information_gain(attributes[1], klass, _training)
        self.assertAlmostEqual(0.102187, ig_for_attr2, 6)
        self.assertEqual('temperature', attributes[1].name)
        ig_for_attr3 = information_gain(attributes[2], klass, _training)
        self.assertAlmostEqual(0.091091, ig_for_attr3, 6)
        self.assertEqual('humidity', attributes[2].name)
        ig_for_attr4 = information_gain(attributes[3], klass, _training)
        self.assertAlmostEqual(0.072780, ig_for_attr4, 6)
        self.assertEqual('windy', attributes[3].name)
        attributes_to_remove = feature_selection.find_attributes_by_ranking('information_gain', 3)
        self.assertEqual(1, len(attributes_to_remove))
        self.assertEqual('windy', attributes_to_remove[0].name)
        
    def test_if_wrapper_options_is_invalid(self):
        self.assertTrue(fs.wrapper_options_invalid(['1R', '3', '5', '6']))
        self.assertTrue(fs.wrapper_options_invalid(['3', '1R']))
        self.assertTrue(fs.wrapper_options_invalid(['1R', 'a']))
        self.assertTrue(fs.wrapper_options_invalid(['1R', '1.0']))
        self.assertTrue(fs.wrapper_options_invalid(['1R', '1']))
        self.assertFalse(fs.wrapper_options_invalid(['1R', '2']))
        self.assertFalse(fs.wrapper_options_invalid(['1R', '2', '5']))
        self.assertTrue(fs.wrapper_options_invalid(['1R', '2', 'a']))
        self.assertFalse(fs.wrapper_options_invalid(['1R', '2', '0.1']))
        
    def test_get_delta(self):
        feature_selection = fs.FeatureSelection(None, None, None, None, None, ['IG','3', '5'])
        self.assertEqual(5, feature_selection.get_delta())
        feature_selection = fs.FeatureSelection(None, None, None, None, None, ['IG','3'])
        self.assertEqual(0, feature_selection.get_delta())
        
    def test_get_fold(self):
        feature_selection = fs.FeatureSelection(['trainingn'] * 4, None, None, None, None, ['IG','3', '5'])
        self.assertEqual(3, feature_selection.get_fold())
        
        feature_selection = fs.FeatureSelection(['trainingn'] * 14, None, None, None, None, ['IG'])
        self.assertEqual(10, feature_selection.get_fold())
        
    def test_invert_attrbute_selection(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        _attributes, _klass = metadata(path)
        feature_selection = fs.FeatureSelection(None, _attributes, None, None, None, ['IG'])
        unselected = feature_selection.invert_attribute_selection([_attributes[0], _attributes[1]])
        self.assertEqual(len(_attributes) - 2, len(unselected))
        self.assertEqual([_attributes[2], _attributes[3], _attributes[4], _attributes[5], _attributes[6], _attributes[7]], unselected)
        
    def test_is_float(self):
        self.assertTrue(fs.isfloat('1.2'))
        self.assertTrue(fs.isfloat('1'))
        self.assertTrue(fs.isfloat('0'))
        self.assertFalse(fs.isfloat('a'))
        
    ## calculations included by using verify variables and comments
    def test_forward_select(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        _training = training(path)
        _attributes, _klass = metadata(path)
        _test = test(path)
        _gold = gold(path)
        
        verify_training = copy.deepcopy(_training)
        verify_attributes = copy.deepcopy(_attributes)

        feat_sel = fs.FeatureSelection(_training, _attributes, _klass, _test, _gold, ['1R', '4', '0.1'])
        feat_sel.forward_selection()
                
        self.assertEqual(1, len(_attributes))
        self.assertEqual('outlook', _attributes[0].name)
        self.verify_number_of_attributes(_training, 1)
        self.verify_number_of_attributes(_test, 1)
        self.verify_number_of_attributes(_gold, 1)

        #verification
        verification_cv_datasets = verify_training.cross_validation_datasets(4)
        accuracies = {}
        for attribute in verify_attributes:
            accuracies[attribute.name] = feat_sel.avg_accuracy_by_cross_validation(verification_cv_datasets, 4, attr.Attributes([attribute]))
        
        #'windy': 0.41666666666666663, 'outlook': 0.79166666666666663, 'temperature': 0.41666666666666663, 'humidity': 0.54166666666666663
        self.assertAlmostEqual(0.4166666, accuracies['windy'], 6)
        self.assertAlmostEqual(0.79166666, accuracies['outlook'], 6)
        self.assertAlmostEqual(0.4166666, accuracies['temperature'], 6)
        self.assertAlmostEqual(0.5416666, accuracies['humidity'], 6)
        
        #outlook selected
        accuracies = {}
        for each in verify_attributes:
            if each.name == 'outlook':
                outlook = each
        verify_attributes.remove(outlook)
        for attribute in verify_attributes:
            accuracies[('outlook',attribute.name)] = feat_sel.avg_accuracy_by_cross_validation(verification_cv_datasets, 4, attr.Attributes([outlook, attribute]))
        
        #{('outlook', 'humidity'): 0.79166666666666663, ('outlook', 'temperature'): 0.79166666666666663, ('outlook', 'windy'): 0.54166666666666663}
        self.assertAlmostEqual(0.7916666, accuracies[('outlook','humidity')], 6)
        self.assertAlmostEqual(0.7916666, accuracies['outlook', 'temperature'], 6)
        self.assertAlmostEqual(0.5416666, accuracies[('outlook','windy')], 6)

    ## calculations included by using verify variables and comments
    def test_backward_select(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        _training = training(path)
        _attributes, _klass = metadata(path)
        _test = test(path)
        _gold = gold(path)
        
        verify_training = copy.deepcopy(_training)
        verify_attributes = copy.deepcopy(_attributes)

        feat_sel = fs.FeatureSelection(_training, _attributes, _klass, _test, _gold, ['1R', '4', '0.1'])
        feat_sel.backward_elimination()
                
        self.assertEqual(3, len(_attributes))
        self.verify_number_of_attributes(_training, 3)
        self.verify_number_of_attributes(_test, 3)
        self.verify_number_of_attributes(_gold, 3)

        #verification
        #level 0
        avg_acc = feat_sel.avg_accuracy_by_cross_validation(verify_training.cross_validation_datasets(4), 4, verify_attributes)
        self.assertAlmostEqual(0.5416666, avg_acc, 6)
        
        verification_cv_datasets = verify_training.cross_validation_datasets(4)
        accuracies = {}
        for attribute in verify_attributes:
            attributes = verify_attributes[:]
            attributes.remove(attribute)
            accuracies[(attributes[0].name,attributes[1].name,attributes[2].name)] = feat_sel.avg_accuracy_by_cross_validation(verification_cv_datasets, 4, attr.Attributes(attributes))
        
#        {('outlook', 'humidity', 'windy'): 0.54166666666666663, 
#        ('outlook', 'temperature', 'windy'): 0.54166666666666663, 
#        ('temperature', 'humidity', 'windy'): 0.29166666666666663, 
#        ('outlook', 'temperature', 'humidity'): 0.79166666666666663}

        self.assertAlmostEqual(0.5416666, accuracies[('outlook', 'humidity', 'windy')], 6)
        self.assertAlmostEqual(0.5416666, accuracies[('outlook', 'temperature', 'windy')], 6)
        self.assertAlmostEqual(0.2916666, accuracies[('temperature', 'humidity', 'windy')], 6)
        self.assertAlmostEqual(0.7916666, accuracies[('outlook', 'temperature', 'humidity')], 6)
#        
        #('outlook', 'temperature', 'humidity') selected
        accuracies = {}

        for each in verify_attributes:
            if each.name == 'windy':
                windy = each
        verify_attributes.remove(windy)
        for attribute in verify_attributes:
            attributes = verify_attributes[:]
            attributes.remove(attribute)
            accuracies[(attributes[0].name,attributes[1].name)] = feat_sel.avg_accuracy_by_cross_validation(verification_cv_datasets, 4, attr.Attributes(attributes))
        
        self.assertAlmostEqual(0.7916666, accuracies[('outlook','humidity')], 6)
        self.assertAlmostEqual(0.7916666, accuracies['outlook', 'temperature'], 6)
        self.assertAlmostEqual(0.4166666, accuracies[('temperature','humidity')], 6)
        
    def test_get_suffix_replaces_decimal_point_in_options_with_hyphen(self):
        feat_sel = FeatureSelectStub()
        feat_sel.run(['-a', 'RNK', '-f', 'path', '-o', 'IG,4'])
        self.assertEqual('-f_RNK_IG_4', feat_sel.get_suffix())

        feat_sel = FeatureSelectStub()
        feat_sel.run(['-a', 'FS', '-f', 'path', '-o', '0R,4,0.34'])
        self.assertEqual('-f_FS_0R_4_0-34', feat_sel.get_suffix())
        
    def verify_number_of_attributes(self, instances, number):
        for instance in instances:
            self.assertEqual(number, len(instance.attrs))
        
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
        self.log = open('test_log', 'w') # w to over write previous logs.. is append mode in code
        
    def error(self, message):
        #in reality error will display usage and quit
        self.message = message
        self.error_called = True
        
    def select_features_and_write_to_file(self):
        pass
