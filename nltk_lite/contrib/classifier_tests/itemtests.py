# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import item
import unittest

class ItemTestCase(unittest.TestCase):
    def testRemovesNewLineAndWhitespace(self):
        i = item.Item('f,g,h\n')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())
        i = item.Item('f, g , h')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())
        i = item.Item('f, g, h\n')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())
        
    def testNameItemRemovesDotAndNewLine(self):
        i = item.NameItem('a,b,c.\n')
        self.assertEqual('a,b,c', i.processed(), 'dot and slash should be removed')
        
    def testIsAttributeReturnsFalseForClasses(self):
        i = item.NameItem('a,b,c.\n')
        self.assertFalse(i.isAttribute(), 'it is not an attribute')
        
    def testIsAttributeReturnsTrueForAttribute(self):
        i = item.NameItem('temp: high, low.\n')
        self.assertTrue(i.isAttribute(), 'it is an attribute')
        
    def testClassValueDoesNotIncludeSpace(self):
        i = item.NameItem('a ,b,c')
        self.assertEqual('a,b,c', i.processed(), 'should not have whitespaces in the string')
        
    def testAttributeValuesDoNotHaveWhitespace(self):
        i = item.NameItem('foo : a , b, c')
        self.assertEqual('foo:a,b,c', i.processed(), 'should not have whitespaces in the string')