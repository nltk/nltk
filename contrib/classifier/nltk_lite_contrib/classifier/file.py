# Natural Language Toolkit - File
#  Understands operations on files and the various input files extensions
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import item, os, exceptions.filenotfounderror as fnf

DOT = '.'
DATA = 'data'
TEST = 'test'
GOLD = 'gold'
NAMES = 'names'

class File:
    def __init__(self, path, extension):
        self.path = path + DOT + extension
        
    def execute(self, obj, methodName, rW = 'r'):
        if not os.path.isfile(self.path): raise fnf.FileNotFoundError(self.path)
        f = open(self.path, rW)
        for l in f:
            getattr(obj, methodName)(l)
        f.close()