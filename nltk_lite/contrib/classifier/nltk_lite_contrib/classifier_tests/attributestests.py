# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import attributes as a, attribute as attr
from nltk_lite_contrib.classifier_tests import *

class AttributesTestCase(unittest.TestCase):
    def setUp(self):
        #make sure you run all tests from the tests directory
        self.attrs = a.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')    
    
    def testCountsCorrectNumberOfAttributes(self):
        self.assertEqual(5, len(self.attrs), 'there should be 5 attributes')
        
    def testAttributesAreValid(self):
        self.assertTrue(self.attrs.hasValues(['dual', 'big', 'symbian', 'y', 'y']))

    def testAttributesAreInOrder(self):
        self.assertEqual('band', self.attrs[0].name)
        self.assertEqual('size', self.attrs[1].name)
        self.assertEqual('os', self.attrs[2].name)
        self.assertEqual('pda', self.attrs[3].name)
        self.assertEqual('mp3', self.attrs[4].name)
        
    def testAttributesContainAnAttribute(self):
        self.assertTrue(self.attrs.__contains__(attr.Attribute('band:dual,tri,quad')))

    def testAttributesAreEqual(self):
        same = a.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(self.attrs, same, 'they should be the same')
        other = a.Attributes(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertNotEqual(self.attrs, other, 'shouldnt be the same')