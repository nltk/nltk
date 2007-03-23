# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import attribute as a
from nltk_lite_contrib.classifier_tests import *

class AttributeTestCase(unittest.TestCase):
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
