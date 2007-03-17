# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import oner, instances as ins
from nltk_lite_contrib.classifier_tests import *

class OneRTestCase(unittest.TestCase):
    def testCreatesDecisionStumpsForEachAttribute(self):
        training = oner.OneRTrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        decisionStumps = training.createEmptyDecisionStumps()
        self.assertEqual(4, len(decisionStumps))
        
    def testReturnsDecisionStumpWithMinimumError(self):
        training = oner.OneRTrainingInstances(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        minError = training.bestDecisionStump()
        self.assertAlmostEqual(0.2222222, minError.error())
        
