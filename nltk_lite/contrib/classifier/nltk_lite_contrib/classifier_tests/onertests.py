# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import oner, instances as ins
from nltk_lite_contrib.classifier_tests import *

class OneRTestCase(unittest.TestCase):
    
    def setUp(self):
        self.WEATHER = datasetsDir(self) + 'minigolf' + SEP + 'weather'
    
    def test_creates_decision_stumps_for_each_attribute(self):
        training = oner.OneRTrainingInstances(self.WEATHER)
        decision_stumps = training.create_empty_decision_stumps()
        self.assertEqual(4, len(decision_stumps))
        
    def test_returns_decision_stump_with_minimum_error(self):
        training = oner.OneRTrainingInstances(self.WEATHER)
        minError = training.best_decision_stump()
        self.assertAlmostEqual(0.2222222, minError.error())
        
    def test_classifies_test_with_stump(self):
        classifier = oner.OneR(self.WEATHER)
        classifier.test(self.WEATHER, False)
        self.assertTrue(classifier.test_instances.instances[0].classifiedKlass is not None)
        self.assertEqual('yes', classifier.test_instances.instances[0].classifiedKlass)
        
    def test_verifies_classification(self):
        classifier = oner.OneR(self.WEATHER)
        cm = classifier.verify(self.WEATHER)
        self.assertEqual(0.5, cm.accuracy())
        self.assertAlmostEqual(0.6666667, cm.fscore())
        
