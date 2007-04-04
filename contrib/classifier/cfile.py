# Natural Language Toolkit - File
#  Understands operations on files and the various input files extensions
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf
import os

DOT = '.'
DATA = 'data'
TEST = 'test'
GOLD = 'gold'
NAMES = 'names'

class File:
    def __init__(self, path, extension):
        self.path = path + DOT + extension
        
    def execute(self, method, r_w = 'r'):
        if not os.path.isfile(self.path): 
            raise fnf.FileNotFoundError(self.path)
        fil = open(self.path, r_w)
        for line in fil:
            method(line)
        fil.close()