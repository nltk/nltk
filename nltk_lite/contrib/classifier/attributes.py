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
        self.path = path
        self.attributes = []
        self.__index = 0
        cfile.File(path, cfile.NAMES).for_each_line(self.create_and_append_values)
                
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
            if self.attributes[i].is_continuous(): continue #do not test continuous attributes
            if not self.attributes[i].has_value(test_value): return False
        return True
    
    def has_continuous_attributes(self):
        for attribute in self.attributes:
            if attribute.is_continuous(): 
                return True
        return False
    
    def subset(self, indices):
        subset = []
        for index in indices:
            subset.append(self.attributes[index])
        return subset

    def discretise(self, discretised_attributes):
        for disc_attr in discretised_attributes:
            self.attributes[disc_attr.index] = disc_attr

    def write_to_file(self, suffix):
        _new_file = cfile.File(self.path + suffix, cfile.NAMES)
        _new_file.create(True)
        lines = []
        for attribute in self.attributes:
            lines.append(attribute.as_line())
        _new_file.write(lines)
        return self.path + suffix + '.' +cfile.NAMES
    
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