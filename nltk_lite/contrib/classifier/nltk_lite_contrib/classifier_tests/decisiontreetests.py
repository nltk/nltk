from nltk_lite_contrib.classifier_tests import *
from nltk_lite_contrib.classifier import decisiontree

class DecisionTreeTestCase(unittest.TestCase):
    def test_tree_creation(self):
        dt = decisiontree.DecisionTree(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual(0, dt.depth())