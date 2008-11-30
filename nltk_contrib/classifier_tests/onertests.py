# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import oner, instances as ins, format
from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier.exceptions import invaliddataerror as inv

class OneRTestCase(unittest.TestCase):
    
    def setUp(self):
        path = self.WEATHER = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        self.classifier = oner.OneR(training(path), attributes(path), klass(path))
        self.classifier.train()
                
    def test_best_decision_stump_returns_minimum_error_stump_by_default(self):
        minError = self.classifier.best_decision_stump(self.classifier.training)
        self.assertAlmostEqual(0.2222222, minError.error())
        
    def test_classifies_test_with_stump(self):
        self.classifier.test(test(self.WEATHER))
        self.assertTrue(self.classifier.test_instances[0].classified_klass is not None)
        self.assertEqual('yes', self.classifier.test_instances[0].classified_klass)
        
    def test_verifies_classification(self):
        cm = self.classifier.verify(gold(self.WEATHER))
        self.assertEqual(0.5, cm.accuracy())
        self.assertAlmostEqual(0.6666667, cm.fscore())
        
    def test_best_decision_stump_uses_the_passed_in_algorithm(self):
        path = self.WEATHER
        classifier = OneRStub(training(path), attributes(path), klass(path))
        self.assertEqual("dummy Best Decision stump", classifier.best_decision_stump(classifier.training, [], 'dummy_algorithm'))
        
    def test_throws_error_for_invalid_algorithm(self):
        try:
            self.classifier.best_decision_stump(self.classifier.training, [], 'invalid_algorithm')
            self.fail('should throw error')
        except inv.InvalidDataError:
            pass
    
    def test_throws_error_for_continuous_attributes(self):
        try:
            path = datasetsDir(self) + 'numerical' + SEP + 'weather'
            classifier = oner.OneR(training(path), attributes(path), klass(path))
            classifier.train()
            self.fail('should have thrown error')
        except inv.InvalidDataError:
            pass
        
        
class OneRStub(oner.OneR):
    def __init__(self, instances, attributes, klass):
        oner.OneR.__init__(self, instances, attributes, klass)
        
    def dummy_algorithm(self, decision_stumps):
        return "dummy Best Decision stump"
