# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier import decisiontree, decisionstump as ds, instances as ins, attribute as attr
from nltk_contrib.classifier.exceptions import invaliddataerror as inv

class DecisionTreeTestCase(unittest.TestCase):
    def test_tree_creation(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        a, c = metadata(path)
        tree = decisiontree.DecisionTree(training(path), a, c)
        tree.train()
        self.assertNotEqual(None, tree)
        self.assertNotEqual(None, tree.root)
        self.assertEqual('band', tree.root.attribute.name)
        self.assertEqual(1, len(tree.root.children))
        self.assertEqual('size', tree.root.children['tri'].attribute.name)
        
    def test_filter_does_not_affect_the_original_training(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        a, c = metadata(path)
        tree = decisiontree.DecisionTree(training(path), a, c)
        tree.train()
        outlook = tree.attributes[0]
        self.assertEqual(9, len(tree.training))
        filtered = tree.training.filter(outlook, 'sunny')
        self.assertEqual(9, len(tree.training))
        self.assertEqual(4, len(filtered))
        
    def test_maximum_information_gain_stump_is_selected(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        _training = training(path)
        a, c = metadata(path)
        tree = decisiontree.DecisionTree(_training, a, c)
        decision_stumps = tree.possible_decision_stumps([], _training)

        max_ig_stump = tree.maximum_information_gain(decision_stumps)
        self.assertEqual('band', max_ig_stump.attribute.name)
        
    def test_maximum_gain_raito_stump_is_selected(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        _training = training(path)
        a, c = metadata(path)
        tree = decisiontree.DecisionTree(_training, a, c)
        decision_stumps = tree.possible_decision_stumps([], _training)
        
        max_gr_stump = tree.maximum_gain_ratio(decision_stumps)
        self.assertEqual('pda', max_gr_stump.attribute.name)
        

        #                     outlook
        #               sunny  / | \ rainy
        #                     /  |  \
        #           temperature       windy
        #             
    def test_ignores_selected_attributes_in_next_recursive_iteration(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        a, c = metadata(path)
        tree = decisiontree.DecisionTree(training(path), a, c)
        tree.train()
        self.assertEqual('outlook', tree.root.attribute.name)
        children = tree.root.children
        self.assertEqual(2, len(children))
        
        sunny = children['sunny']
        self.assertEqual('temperature', sunny.attribute.name)
        self.assertEqual(0, len(sunny.children))
        
        rainy = children['rainy']
        self.assertEqual('windy', rainy.attribute.name)
        self.assertEqual(0, len(rainy.children))

    def test_throws_error_if_conitinuous_atributes_are_present(self):
        try:
            path = datasetsDir(self) + 'numerical' + SEP + 'weather'
            a,c = metadata(path)
            dt = decisiontree.DecisionTree(training(path), a, c)
            dt.train()
            self.fail('should have thrown an error')
        except inv.InvalidDataError:
            pass
            
        
