# Natural Language Toolkit - Item
#  An item should be capable of operating on its string value
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

import re

class Item:
    def __init__(self, line):
        self.line = line
    
    def stripNewLineAndWhitespace(self):
        nonewline = self.line.strip()
        return re.compile(' ').sub('', nonewline)

class NameItem(Item):
    def __init__(self, line):
        Item.__init__(self, line)
    
    def processed(self):
        return re.compile('\.$').sub('', self.stripNewLineAndWhitespace())
    
    def isAttribute(self):
        return self.line.find(':') != -1
