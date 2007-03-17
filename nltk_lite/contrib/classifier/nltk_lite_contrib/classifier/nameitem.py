# Natural Language Toolkit - NameItem
#  An extension to Item, it is specific to strings encountered while 
#     creating an Attribute
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import item
import re

class NameItem(item.Item):
    def __init__(self, line):
        item.Item.__init__(self, line)
    
    def processed(self):
        return re.compile('\.').sub('', self.stripNewLineAndWhitespace())
    
    def isAttribute(self):
        return re.compile(':').search(self.line) != None