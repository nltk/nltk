# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import oner, instances as ins, format
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

class OneRTestCase(unittest.TestCase):
    
    def setUp(self):
        path = self.WEATHER = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        c45 = format.C45_FORMAT
        self.classifier = oner.OneR(c45.get_training_instances(path), c45.get_attributes(path), c45.get_klass(path), c45)
                
    def test_creates_decision_stumps_for_each_attribute(self):
        self.classifier.create_empty_decision_stumps([])
        self.assertEqual(4, len(self.classifier.decision_stumps))
        
    def test_best_decision_stump_returns_minimum_error_stump_by_default(self):
        minError = self.classifier.best_decision_stump(self.classifier.training)
        self.assertAlmostEqual(0.2222222, minError.error())
        
    def test_classifies_test_with_stump(self):
        self.classifier.test(format.C45_FORMAT.get_test_instances(self.WEATHER), False)
        self.assertTrue(self.classifier.test_instances[0].classifiedKlass is not None)
        self.assertEqual('yes', self.classifier.test_instances[0].classifiedKlass)
        
    def test_verifies_classification(self):
        cm = self.classifier.verify(format.C45_FORMAT.get_gold_instances(self.WEATHER))
        self.assertEqual(0.5, cm.accuracy())
        self.assertAlmostEqual(0.6666667, cm.fscore())
        
    def test_best_decision_stump_uses_the_passed_in_algorithm(self):
        path = self.WEATHER
        c45 = format.C45_FORMAT
        classifier = OneRStub(c45.get_training_instances(path), c45.get_attributes(path), c45.get_klass(path), c45)
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
            c45 = format.C45_FORMAT
            classifier = oner.OneR(c45.get_training_instances(path), c45.get_attributes(path), c45.get_klass(path), c45)
            self.fail('should have thrown error')
        except inv.InvalidDataError:
            pass
        
        
class OneRStub(oner.OneR):
    def __init__(self, instances, attributes, klass, format):
        oner.OneR.__init__(self, instances, attributes, klass, format)
        
    def dummy_algorithm(self):
        return "dummy Best Decision stump"
