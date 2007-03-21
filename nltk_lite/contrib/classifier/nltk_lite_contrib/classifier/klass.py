# Natural Language Toolkit - Klass
#  Creates the Class attribute from a '.names' file
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import nameitem as ni, file

class Klass:
    def __init__(self, path):
        self.__processed, self.__byValue = False, {}
        file.File(path, file.NAMES).execute(self, 'create_klass')
        
    def create_klass(self, l):
        if not self.__processed:
            self.values = ni.NameItem(l).processed().split(',')
            self.__processed = True
            
    def has_value(self, toTest):
        return self.values.__contains__(toTest)
    
    def valuesWith0Count(self):
        map = {}
        for value in self.values:
            map[value] = 0
        return map
    
    def __len__(self):
        return len(self.values)
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.values == other.values: return True
        return False 
    
    def __str__(self):
        return self.values.join(',')
        
           

         
