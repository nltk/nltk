# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import nameitem as ni
import unittest

class NameItemTestCase(unittest.TestCase):
    def testRemovesDotAndNewLine(self):
        item = ni.NameItem('a,b,c.\n')
        self.assertEqual('a,b,c', item.processed(), 'dot and slash should be removed')
        
    def testIsAttributeReturnsFalseForClasses(self):
        item = ni.NameItem('a,b,c.\n')
        self.assertFalse(item.isAttribute(), 'it is not an attribute')
        
    def testIsAttributeReturnsTrueForAttribute(self):
        item = ni.NameItem('temp: high, low.\n')
        self.assertTrue(item.isAttribute(), 'it is an attribute')
        
    def testClassValueDoesNotIncludeSpace(self):
        item = ni.NameItem('a ,b,c')
        self.assertEqual('a,b,c', item.processed(), 'should not have whitespaces in the string')
        
    def testAttributeValuesDoNotHaveWhitespace(self):
        item = ni.NameItem('foo : a , b, c')
        self.assertEqual('foo:a,b,c', item.processed(), 'should not have whitespaces in the string')