# Natural Language Toolkit - Attributes
#  Understands that attributes are created in order from a '.names' file
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

import nameitem as ni, attribute as a, cfile

class Attributes:
    def __init__(self, path):
        self.attributes = []
        self.__index = 0
        cfile.File(path, cfile.NAMES).execute(self.create_and_append_values)
                
    def create_and_append_values(self, l):
        nameitem = ni.NameItem(l)      
        processed = nameitem.processed()
        if not len(processed) == 0 and nameitem.isAttribute():
            self.attributes.append(a.Attribute(processed, self.__index))
            self.__index += 1

    def has_values(self, test_values):
        if len(test_values) != len(self): return False
        for i in range(len(test_values)):
            test_value = test_values[i]
            if not self.attributes[i].has_value(test_value): return False
        return True

    def __len__(self):
        return len(self.attributes)
    
    def __getitem__(self, index):
        return self.attributes[index]
    
    def __contains__(self, other):
        return self.attributes.__contains__(other)

    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.attributes == other.attributes: return True
        return False