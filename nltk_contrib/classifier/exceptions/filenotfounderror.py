# Natural Language Toolkit - FileNotFound Error
#  Is thrown when a file cannot be found at the path specified
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

import os

class FileNotFoundError:
    def __init__(self, path):
        self.msg = 'cannot find file at ' + os.path.abspath(path)
    
    def __str__(self):
        return self.msg
