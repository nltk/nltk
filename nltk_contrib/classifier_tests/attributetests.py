# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import attribute as a
from nltk_contrib.classifier_tests import *
import math

class AttributeTestCase(unittest.TestCase):
    def test_attribute_creation(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        self.assertEqual('foo', attr.name)
        self.assertEqual(['a', 'b', 'c'], attr.values)
    
    def test_returns_true_if_value_is_present(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        self.assertTrue(attr.has_value('c'))
        self.assertFalse(attr.has_value('d'))
        
    def test_equality(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        same = a.Attribute('foo', ['a','b','c'], 0)
        othername = a.Attribute('foobar', ['a','b','c'], 1)
        otherval = a.Attribute('foo',['a','b','c','d'], 0)
        self.assertEqual(attr, same, 'they should be equal')
        self.assertNotEqual(attr, othername, 'they are not equal')
        self.assertNotEqual(attr, otherval, 'they are not equal')
            
    def test_is_countinuous_returns_true_if_continuous(self):
        cont_attr = a.Attribute('temperature',['continuous'], 1)
        self.assertEqual(a.CONTINUOUS, cont_attr.type)
        self.assertTrue(cont_attr.is_continuous())
        
        disc_attr = a.Attribute('foo',['a','b','c'], 0)
        self.assertEqual(a.DISCRETE, disc_attr.type)
        self.assertFalse(disc_attr.is_continuous())
                
    def test_empty_freq_dists(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        freq_dists = attr.empty_freq_dists()
        self.assertEqual(3, len(freq_dists))
        for each in attr.values:
            self.assertEqual(0, freq_dists[each].N())
        
    def test_values_as_str(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        self.assertEqual('a,b,c', attr.values_as_str())
        
    def test_to_string(self):
        attr = a.Attribute('foo', ['a','b','c'], 0)
        self.assertEqual('foo:[a,b,c] index:0', str(attr))
        
