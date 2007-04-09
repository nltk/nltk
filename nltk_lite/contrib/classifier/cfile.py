# Natural Language Toolkit - File
#  Understands operations on files and the various input files extensions
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
import os, os.path

DOT = '.'
DATA = 'data'
TEST = 'test'
GOLD = 'gold'
NAMES = 'names'

class File:
    def __init__(self, path, extension):
        self.path = path + DOT + extension
        
    def for_each_line(self, method):
        self.__check_for_existence()
        fil = open(self.path, 'r')
        for line in fil:
            method(line)
        fil.close()

    def __check_for_existence(self):
        if not os.path.isfile(self.path): 
            raise fnf.FileNotFoundError(self.path)
        
    def create(self, overwrite = False):
        if not overwrite and os.path.exists(self.path):
            raise inv.InvalidDataError('File or Directory exists at ' + self.path + ' and overwrite is set to false.')
        if os.path.exists(self.path): 
            if os.path.isfile(self.path):
                os.remove(self.path)
            else:
                raise inv.InvalidDataError('Cannot overwrite directory ' + self.path + '.')
        fil = open(self.path, 'w')
        fil.close()
        
    def write(self, lines):
        self.__check_for_existence()
        fil = open(self.path, 'w')
        for line in lines:
            fil.write(line)
            fil.write('\n')
        fil.close()
        
def name_extension(file_name):
    dot_index = file_name.rfind(DOT)
    if dot_index == -1:
        return [file_name, '']
    return [file_name[:dot_index], file_name[dot_index+1:]]