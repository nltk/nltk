# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import oner, instances as ins
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

class OneRTestCase(unittest.TestCase):
    
    def setUp(self):
        self.WEATHER = datasetsDir(self) + 'minigolf' + SEP + 'weather'
    
    def test_creates_decision_stumps_for_each_attribute(self):
        classifier = oner.OneR(self.WEATHER)
        classifier.create_empty_decision_stumps([])
        self.assertEqual(4, len(classifier.decision_stumps))
        
    def test_best_decision_stump_returns_minimum_error_stump_by_default(self):
        classifier = oner.OneR(self.WEATHER)
        minError = classifier.best_decision_stump(classifier.training)
        self.assertAlmostEqual(0.2222222, minError.error())
        
    def test_classifies_test_with_stump(self):
        classifier = oner.OneR(self.WEATHER)
        classifier.test(self.WEATHER, False)
        self.assertTrue(classifier.test_instances[0].classifiedKlass is not None)
        self.assertEqual('yes', classifier.test_instances[0].classifiedKlass)
        
    def test_verifies_classification(self):
        classifier = oner.OneR(self.WEATHER)
        cm = classifier.verify(self.WEATHER)
        self.assertEqual(0.5, cm.accuracy())
        self.assertAlmostEqual(0.6666667, cm.fscore())
        
    def test_best_decision_stump_uses_the_passed_in_algorithm(self):
        classifier = OneRStub(self.WEATHER)
        self.assertEqual("dummy Best Decision stump", classifier.best_decision_stump(classifier.training, [], 'dummy_algorithm'))
        
    def test_throws_error_for_invalid_algorithm(self):
        classifier = OneRStub(self.WEATHER)
        try:
            classifier.best_decision_stump(classifier.training, [], 'invalid_algorithm')
            self.fail('should throw error')
        except inv.InvalidDataError:
            pass
    
    def test_throws_error_for_continuous_attributes(self):
        try:
            classifier = oner.OneR(datasetsDir(self) + 'numerical' + SEP + 'weather')
            self.fail('should have thrown error')
        except inv.InvalidDataError:
            pass
        
        
class OneRStub(oner.OneR):
    def __init__(self, path):
        oner.OneR.__init__(self, path)
        
    def dummy_algorithm(self):
        return "dummy Best Decision stump"
