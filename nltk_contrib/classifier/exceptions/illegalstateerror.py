# Natural Language Toolkit - Illegal state error 
#   Is thrown to show indicate an illegal state in the program
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier.exceptions import SimpleError

class IllegalStateError(SimpleError):
    pass
