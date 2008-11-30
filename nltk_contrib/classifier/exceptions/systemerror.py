# Natural Language Toolkit - System error 
#   Is thrown to show unusual behavior not caused by bad input from the user, 
#   but from a programming mistake.
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier.exceptions import SimpleError

class SystemError(SimpleError):
    pass
