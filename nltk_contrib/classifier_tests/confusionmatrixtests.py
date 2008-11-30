# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import confusionmatrix as cm
from nltk_contrib.classifier.exceptions import systemerror as se
from nltk_contrib.classifier_tests import *

class ConfusionMatrixTestCase(unittest.TestCase):
    def setUp(self):
        self.c = cm.ConfusionMatrix(['yes', 'no'])
        self.pos = 'yes'
        self.neg = 'no'
        
    def test_initial_confusion_matrix_has_all_zero_counts(self):
        self.__assert_matrix(0, 0, 0, 0)
            
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
    
    def test_no_divide_by_zero_error_when_numerators_are_zero(self):
        self.c.count(self.pos, self.neg)
        self.c.count(self.pos, self.neg)
        self.c.count(self.neg, self.neg)
        self.c.count(self.neg, self.neg)
        self.assertEqual(0, self.c.precision())
        self.assertEqual(0, self.c.recall())
        self.assertEqual(0, self.c.fscore())
        self.assertEqual(0.5, self.c.accuracy())
        
    def test_more_klass_values(self):
        c = cm.ConfusionMatrix(['1', '2', '3', '4', '5', 'U'])
        c.count('1', '2')
        c.count('2', '2')
        c.count('2', '3')
        c.count('3', '3')
        c.count('4', '2')
        c.count('5', '5')
        c.count('2', '2')
        c.count('3', '2')
        #matrix values for class '1'
        self.assertEqual(0, c.tp(0))
        self.assertEqual(7, c.tn(0))
        self.assertEqual(1, c.fn(0))
        self.assertEqual(0, c.fp(0))
        #matrix values for class 'U'
        self.assertEqual(0, c.tp(5))
        self.assertEqual(8, c.tn(5))
        self.assertEqual(0, c.fn(5))
        self.assertEqual(0, c.fp(5))
        
        
        self.assertEqual(0.875, c.accuracy())#accuracy for class '1'(default accuracy)
        self.assertEqual(1, c.accuracy(index=5))#accuracy for 'U'
        self.assertEqual(0, c.fscore())#f-score for '1'(default f-score)
        self.assertEqual(0, c.fscore(index=5))#f-score for 'U'
        self.assertEqual(0.5, c.fscore(index=1))#f-score for '2'
        
        
    def __assert_matrix(self, tp, fn, fp, tn):
        self.assertEqual(tp, self.c.tp())
        self.assertEqual(fn, self.c.fn())
        self.assertEqual(fp, self.c.fp())
        self.assertEqual(tn, self.c.tn())
