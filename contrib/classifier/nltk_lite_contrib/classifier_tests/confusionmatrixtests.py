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
        
    def test_initial_confusion_matrix_has_all_zero_counts(self):
        self.__assert_matrix(0, 0, 0, 0)
        
    def test_divide_by_zero_error_thrown_if_den_is_zero(self):
        try:
            self.c.accuracy()
            self.fail('should have thrown system exception')
        except se.SystemError:
            pass
    
    def test_confusion_matrix_updates_on_each_count(self):
        self.__assert_matrix(0, 0, 0, 0)
        self.c.count(self.pos, self.pos)
        self.__assert_matrix(1, 0, 0, 0)
        self.c.count(self.pos, self.pos)
        self.__assert_matrix(2, 0, 0, 0)
        self.c.count(self.pos, self.neg)
        self.__assert_matrix(2, 1, 0, 0)
        self.c.count(self.neg, self.pos)
        self.__assert_matrix(2, 1, 1, 0)
        self.c.count(self.neg, self.neg)
        self.__assert_matrix(2, 1, 1, 1)
        
    def test_calculation_of_accuracy_and_error(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.accuracy())
        self.assertEqual(0.75, self.c.error())
        
    def test_true_positive_rate(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.5, self.c.tpr())
        self.assertEqual(0.5, self.c.sensitivity())
        
    def test_true_negative_rate(self):
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.66666667, self.c.tnr(), 8)
        self.assertAlmostEqual(0.66666667, self.c.specificity(), 8)
        
    def test_false_positive_rate(self):
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.33333333, self.c.fpr(), 8)
        
    def test_precision(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.precision())
        
    def test_recall(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.neg)
        self.assertAlmostEqual(0.66666667, self.c.recall(), 8)
        
    def test_fscore(self):
        self.c.count(self.pos, self.pos)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.c.count(self.neg, self.pos)
        self.assertEqual(0.25, self.c.precision())
        self.assertAlmostEqual(0.5, self.c.recall(), 8)
        self.assertAlmostEqual(0.33333333, self.c.fscore(), 8)
        
    def __assert_matrix(self, tp, fn, fp, tn):
        self.assertEqual(tp, self.c.tp())
        self.assertEqual(fn, self.c.fn())
        self.assertEqual(fp, self.c.fp())
        self.assertEqual(tn, self.c.tn())
