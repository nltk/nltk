# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier_tests import *
from nltk_lite_contrib.classifier import decisiontree, decisionstump as ds, attributes as attrs, klass as k, instances as ins

class DecisionTreeTestCase(unittest.TestCase):
    def test_tree_creation(self):
        tree = decisiontree.DecisionTree(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertNotEqual(None, tree)
        self.assertNotEqual(None, tree.root)
        self.assertEqual('band', tree.root.attribute.name)
        self.assertEqual(1, len(tree.root.children))
        self.assertEqual('size', tree.root.children['tri'].attribute.name)
        
    def test_filter_does_not_affect_the_original_training(self):
        tree = decisiontree.DecisionTree(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        outlook = tree.attributes[0]
        self.assertEqual(9, len(tree.training))
        filtered = tree.training.filter(outlook, 'sunny')
        self.assertEqual(9, len(tree.training))
        self.assertEqual(4, len(filtered))
        
    def test_maximum_informaition_gain_stump_is_selected(self):
        tree = decisiontree.DecisionTree(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        max_ig_stump = tree.maximum_information_gain()
        self.assertEqual('size', max_ig_stump.attribute.name)
        

        #                     outlook
        #               sunny  / | \ rainy
        #                     /  |  \
        #           temperature       windy
        #             
    def test_ignores_selected_attributes_in_next_recursive_iteration(self):
        tree = decisiontree.DecisionTree(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual('outlook', tree.root.attribute.name)
        children = tree.root.children
        self.assertEqual(2, len(children))
        
        sunny = children['sunny']
        self.assertEqual('temperature', sunny.attribute.name)
        self.assertEqual(0, len(sunny.children))
        
        rainy = children['rainy']
        self.assertEqual('windy', rainy.attribute.name)
        self.assertEqual(0, len(rainy.children))
