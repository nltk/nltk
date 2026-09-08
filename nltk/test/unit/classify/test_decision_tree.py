import unittest
from nltk.classify.decision_tree import DecisionTreeClassifier

class TestDecisionTreeClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = DecisionTreeClassifier(max_depth=3)
        self.train_data = [
            ({'feature1': 'yes', 'feature2': 'no'}, 'classA'),
            ({'feature1': 'no', 'feature2': 'yes'}, 'classB'),
            ({'feature1': 'yes', 'feature2': 'yes'}, 'classA'),
            ({'feature1': 'no', 'feature2': 'no'}, 'classB'),
        ]

    def test_train(self):
        self.classifier.train(self.train_data)
        self.assertIsNotNone(self.classifier.tree)

    def test_classify(self):
        self.classifier.train(self.train_data)
        result = self.classifier.classify({'feature1': 'yes', 'feature2': 'no'})
        self.assertIn(result, ['classA', 'classB'])

    def test_information_gain(self):
        gain = self.classifier._information_gain(self.train_data, 'feature1')
        self.assertIsInstance(gain, float)

    # Add more tests as needed

if __name__ == '__main__':
    unittest.main()