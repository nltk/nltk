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
        outlook = tree.training.attributes[0]
        self.assertEqual(9, len(tree.training.instances))
        filtered = tree.training.filter(outlook, 'sunny')
        self.assertEqual(9, len(tree.training.instances))
        self.assertEqual(4, len(filtered.instances))
        
    def test_maximum_informaition_gain_stump_is_selected(self):
        tree = decisiontree.DecisionTree(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        attributes = attrs.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        klass = k.Klass(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        stumps = []
        instances = ins.TrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        for attribute in attributes:
            stump = ds.DecisionStump(attribute, klass)
            stumps.append(stump)
            for instance in instances.instances:
                stump.update_count(instance)

        max_ig_stump = tree.training.maximum_information_gain(stumps)
        self.assertEqual('band', max_ig_stump.attribute.name)
        