# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import klass as k
from nltk_lite_contrib.classifier.exceptions import systemerror as system
from nltk_lite_contrib.classifier_tests import *

class KlassTestCase(unittest.TestCase):
    def setUp(self):
        #make sure you run all tests from the tests directory
        self.phoney = k.Klass(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
    
    def testNumberOfClasses(self):
        self.assertEqual(3, len(self.phoney), '3 class values should be present')
        
    def testTheClassesCreated(self):
        self.assertEqual(['a', 'b', 'c'], self.phoney.values, 'the three class values should be a, b and c')
        
    def testIfClassIsValid(self):
        self.assertTrue(self.phoney.has_value('b'))
        self.assertFalse(self.phoney.has_value('d'))
        
    def testReturnsMapOfAllValuesWithCountAs0(self):
        values = self.phoney.valuesWith0Count();
        self.assertEqual(3, len(values))
        for i in ['a', 'b', 'c']:
            self.assertTrue(values.has_key(i))
            self.assertEqual(0, values[i])

    def testEquality(self):
        self.assertEqual(k.Klass(datasetsDir(self) + 'test_phones' + SEP + 'phoney'), self.phoney)
        