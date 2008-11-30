# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

import unittest, os, re
from nltk_contrib.classifier import format

SEP = os.path.sep

def thisFileDir(self):
    thisfilepath = os.path.abspath(self.__module__)
    return os.path.dirname(re.compile('\.').sub(SEP, thisfilepath))

def datasetsDir(self):
    currentDir = thisFileDir(self)
    while not os.path.exists(os.path.join(currentDir, 'datasets')):
        currentDir = os.path.dirname(currentDir)
    return os.path.join(currentDir, 'datasets') + SEP
    
def training(path):
    return format.c45.training(path)    
    
def test(path):
    return format.c45.test(path)
    
def gold(path):
    return format.c45.gold(path)
    
def metadata(path):
    return format.c45.metadata(path)

def attributes(path):
    attrs, klass = format.c45.metadata(path)
    return attrs

def klass(path):
    attrs, klass = format.c45.metadata(path)
    return klass
