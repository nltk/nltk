# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import unittest, os, re

SEP = os.path.sep

def thisFileDir(self):
    thisfilepath = os.path.abspath(self.__module__)
    return os.path.dirname(re.compile('\.').sub(SEP, thisfilepath))

def datasetsDir(self):
    currentDir = thisFileDir(self)
    while not os.path.exists(os.path.join(currentDir, 'datasets')):
        currentDir = os.path.dirname(currentDir)
    return os.path.join(currentDir, 'datasets') + SEP
    
