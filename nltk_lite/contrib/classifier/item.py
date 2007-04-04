# Natural Language Toolkit - Item
#  An item should be capable of operating on its string value
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import re

class Item:
    def __init__(self, line):
        self.line = line
    
    def stripNewLineAndWhitespace(self):
        nonewline = self.line.strip()
        return re.compile(' ').sub('', nonewline)
