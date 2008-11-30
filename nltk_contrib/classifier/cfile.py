# Natural Language Toolkit - File
#  Understands operations on files and the various input files extensions
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
import os, os.path

DOT = '.'

class File:
    def __init__(self, path, extension):
        self.path = path + DOT + extension
        
    def for_each_line(self, method):
        self.__check_for_existence()
        fil = open(self.path, 'r')
        returned = []
        for line in fil:
            filtered = filter_comments(line)
            if len(filtered) == 0:
                continue
            returned.append(method(filtered))
        fil.close()
        return returned

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
        
def filter_comments(line):
    index = line.find('|')
    if index == -1:
        return line.strip()
    return line[:index].strip()

def name_extension(file_name):
    dot_index = file_name.rfind(DOT)
    if dot_index == -1:
        return [file_name, '']
    return [file_name[:dot_index], file_name[dot_index+1:]]
