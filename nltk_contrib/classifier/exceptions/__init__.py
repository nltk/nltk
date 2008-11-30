# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

class SimpleError:
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return self.message
