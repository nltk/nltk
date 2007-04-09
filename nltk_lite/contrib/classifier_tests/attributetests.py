# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import attribute as a
from nltk_lite.contrib.classifier_tests import *

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
            
    def test_is_countinuous_returns_true_if_continuous(self):
        cont_attr = a.Attribute('temperature:continuous', 1)
        self.assertEqual(a.CONTINUOUS, cont_attr.type)
        self.assertTrue(cont_attr.is_continuous())
        
        disc_attr = a.Attribute('foo:a,b,c', 0)
        self.assertEqual(a.DISCRETE, disc_attr.type)
        self.assertFalse(disc_attr.is_continuous())
        
    def test_as_line(self):
        attr = a.Attribute('foo:a,b,c', 0)
        self.assertEqual('foo:a,b,c', attr.as_line())