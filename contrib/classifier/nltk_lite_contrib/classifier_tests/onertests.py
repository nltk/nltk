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
    
    def testCreatesDecisionStumpsForEachAttribute(self):
        training = oner.OneRTrainingInstances(self.WEATHER)
        decisionStumps = training.createEmptyDecisionStumps()
        self.assertEqual(4, len(decisionStumps))
        
    def testReturnsDecisionStumpWithMinimumError(self):
        training = oner.OneRTrainingInstances(self.WEATHER)
        minError = training.bestDecisionStump()
        self.assertAlmostEqual(0.2222222, minError.error())
        
    def testClassifiesTestWithStump(self):
        test = oner.OneRTestInstances(self.WEATHER)
        classifier = oner.OneR(self.WEATHER)
        classifier.classify(test)
        self.assertTrue(test.instances[0].classifiedKlass is not None)
        self.assertEqual('yes', test.instances[0].classifiedKlass)
        
