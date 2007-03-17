# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import attribute as a
from nltk_lite_contrib.classifier_tests import *

class AttributeTestCase(unittest.TestCase):
    def testAttributeCreation(self):
        attr = a.Attribute('foo:a,b,c')
        self.assertEqual('foo', attr.name)
        self.assertEqual(['a', 'b', 'c'], attr.values)
    
    def testHasValueReturnsTrueIfValueIsPresent(self):
        attr = a.Attribute('foo:a,b,c')
        self.assertTrue(attr.hasValue('c'))
        self.assertFalse(attr.hasValue('d'))
        
    def testEquality(self):
        attr = a.Attribute('foo:a,b,c')
        same = a.Attribute('foo:a,b,c')
        othername = a.Attribute('foobar:a,b,c')
        otherval = a.Attribute('foo:a,b,c,d')
        self.assertEqual(attr, same, 'they should be equal')
        self.assertNotEqual(attr, othername, 'they are not equal')
        self.assertNotEqual(attr, otherval, 'they are not equal')
