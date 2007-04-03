# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import attribute as a
from nltk_lite_contrib.classifier_tests import *

class AttributeTestCase(unittest.TestCase):
    def test_get_name(self):
        self.assertEqual('foo', a.get_name('foo:a,b,c'))

    def test_get_values(self):
        self.assertEqual(['a', 'b', 'c'], a.get_values('foo:a,b,c'))
    
    def test_attribute_creation(self):
        attr = a.Attribute('foo:a,b,c', 0)
        self.assertEqual('foo', attr.name)
        self.assertEqual(['a', 'b', 'c'], attr.values)
    
    def test_returns_true_if_value_is_present(self):
        attr = a.Attribute('foo:a,b,c', 0)
        self.assertTrue(attr.has_value('c'))
        self.assertFalse(attr.has_value('d'))
        
    def test_equality(self):
        attr = a.Attribute('foo:a,b,c', 0)
        same = a.Attribute('foo:a,b,c', 0)
        othername = a.Attribute('foobar:a,b,c', 1)
        otherval = a.Attribute('foo:a,b,c,d', 0)
        self.assertEqual(attr, same, 'they should be equal')
        self.assertNotEqual(attr, othername, 'they are not equal')
        self.assertNotEqual(attr, otherval, 'they are not equal')
            
    def test_create_values(self):
        self.assertEqual(['a', 'b', 'c', 'd', 'e'], a.create_values(5))
        
    def test_binary_search(self):
        self.assertEqual(1, a.binary_search([(2, 4), (4, 6), (6, 8), (8, 10.000001)], 4))
        self.assertEqual(3, a.binary_search([(2, 4), (4, 6), (6, 8), (8, 10.000001)], 10))
        self.assertEqual(-1, a.binary_search([(2, 4), (4, 6), (6, 8), (8, 10.000001)], 1))
        self.assertEqual(-1, a.binary_search([(2, 4), (4, 6), (6, 8), (8, 10.000001)], 11))
        self.assertEqual(-1, a.binary_search([(2, 4), (4, 6), (6, 8.000001)], 9))
        self.assertEqual(2, a.binary_search([(2, 4), (4, 6), (6, 8.000001)], 8))
        self.assertEqual(0, a.binary_search([(6.0, 14.666666666666666), (14.666666666666666, 23.333333333333332), (23.333333333333332, 32.000000999999997)], 12))
        
    def test_unsupervised_equal_width(self):
        attr = a.Attribute('temperature:12,17.9,18,6,21,27.5,32.0,10.7,28.3,22,25.4,14.1,9', 1)
        mapping = attr.unsupervised_equal_width(3)
        self.assertEqual(13, len(attr.values))
        self.assertEqual('a', mapping[float('12')])
        self.assertEqual('a', mapping[float('12.0')])
        self.assertEqual('a', mapping[6])
        self.assertEqual('c', mapping[32.0])
        self.assertEqual('c', mapping[28.3])
        self.assertEqual('b', mapping[17.9])