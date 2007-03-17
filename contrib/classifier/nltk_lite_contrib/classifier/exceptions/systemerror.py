# Natural Language Toolkit - System error 
#   Is thrown to show unusual behavior not caused by bad input from the user, 
#   but from a programming mistake.
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

class SystemError:
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return message
    