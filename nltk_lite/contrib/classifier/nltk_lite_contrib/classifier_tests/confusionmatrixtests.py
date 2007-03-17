# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import confusionmatrix as cm, klass as k
from nltk_lite_contrib.classifier.exceptions import systemerror as se
from nltk_lite_contrib.classifier_tests import *

class ConfusionMatrixTestCase(unittest.TestCase):
    def setUp(self):
        weather = k.Klass(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.c = cm.ConfusionMatrix(weather)
        self.pos = 'yes'
        self.neg = 'no'
        
    def testInitialConfusionMatrixHasAllZeroCounts(self):
        self.assertMatrix(0, 0, 0, 0)
        
    def testDivideByZeroErrorThrownIfDenIsZero(self):
        try:
            self.c.accuracy()
            fail('should have thrown system exception')
        except se.SystemError:
            pass
    
    def testConfusionMatrixUpdatesOnEachCount(self):
        self.assertMatrix(0, 0, 0, 0)
        self.c.count(self.pos, self.pos)
        self.assertMatrix(1, 0, 0, 0)
        self.c.count(self.pos, self.pos)
        self.assertMatrix(2, 0, 0, 0)
        self.c.count(self.pos, self.neg)
        self.assertMatrix(2, 1, 0, 0)
        self.c.count(self.neg, self.pos)
        self.assertMatrix(2, 1, 1, 0)
        self.c.count(self.neg, self.neg)
        self.assertMatrix(2, 1, 1, 1)
        
    def testCalculationOfAccuracyAndError(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.accuracy())
        self.assertEqual(0.75, self.c.errorRate())
        
    def testTruePositiveRate(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.5, self.c.tpr())
        self.assertEqual(0.5, self.c.sensitivity())
        
    def testTrueNegativeRate(self):
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.66666667, self.c.tnr(), 8)
        self.assertAlmostEqual(0.66666667, self.c.specificity(), 8)
        
    def testFalsePositiveRate(self):
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.33333333, self.c.fpr(), 8)
        
    def testPrecision(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.precision())
        
    def testRecall(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.66666667, self.c.recall(), 8)
        
    def testFscore(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.precision())
        self.assertAlmostEqual(0.5, self.c.recall(), 8)
        self.assertAlmostEqual(0.33333333, self.c.fscore(), 8)
        
    def assertMatrix(self, tp, fn, fp, tn):
        self.assertEqual(tp, self.c.tp())
        self.assertEqual(fn, self.c.fn())
        self.assertEqual(fp, self.c.fp())
        self.assertEqual(tn, self.c.tn())
