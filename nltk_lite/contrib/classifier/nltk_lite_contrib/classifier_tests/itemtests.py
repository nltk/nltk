# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import item
import unittest

class ItemTestCase(unittest.TestCase):
    def testRemovesNewLineAndWhitespace(self):
        i = item.Item('f,g,h\n')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())
        i = item.Item('f, g , h')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())
        i = item.Item('f, g, h\n')
        self.assertEqual('f,g,h', i.stripNewLineAndWhitespace())