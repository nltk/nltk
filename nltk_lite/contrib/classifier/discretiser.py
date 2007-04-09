# Natural Language Toolkit - Discretiser
#  Capable of dicretising numeric values into dicrete attributes
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
from nltk_lite.contrib.classifier import instances as ins, attributes as attrs, discretisedattribute as da, cfile as f

class Discretiser:
    def __init__(self, path, test_files, attribute_indices, options):
        self.training = ins.TrainingInstances(path)
        self.attributes = attrs.Attributes(path)
        self.instances = self.create_instances(self.__test_files(test_files))
        self.attribute_indices = self.__as_integers('Attribute indices', attribute_indices)
        self.options = self.__as_integers('Options', options)
        
    def __test_files(self, file_names):
        _file_names = []
        for name in file_names.split(','):
            _file_names.append(name.strip())
        return _file_names
    
    def __as_integers(self, name, attribute_indices):
        indices = []
        for attribute_index in attribute_indices.split(','):
            try:
                indices.append(int(attribute_index.strip()))
            except ValueError:
                raise inv.InvalidDataError('Invalid Data. ' + name + ' should be integers.')
        return indices
                    
    def unsupervised_equal_width(self):
        attrs = self.attributes.subset(self.attribute_indices)
        ranges = self.training.as_ranges(attrs)
        disc_attrs = self.discretised_attributes(ranges)
        to_be_discretised = [self.attributes, self.training] + self.instances
        
        for each in to_be_discretised:
            each.discretise(disc_attrs)
            each.write_to_file('d')

    def discretised_attributes(self, ranges):
        discretised_attributes = []
        for index in range(len(self.options)):
            _range, width = ranges[index], self.options[index]
            attribute_index = self.attribute_indices[index]
            attribute = self.attributes[attribute_index]
            discretised_attributes.append(da.DiscretisedAttribute(attribute.name, _range.split(width), attribute.index))
        return discretised_attributes
            
    def create_instances(self, files):
        instances = []
        for file_name in files:
            name, extension = f.name_extension(file_name)
            if extension == f.TEST:
                instances.append(ins.TestInstances(name))
            elif extension == f.GOLD:
                instances.append(ins.GoldInstances(name))
            elif extension == f.DATA:
                instances.append(ins.TrainingInstances(name))
            else:
                raise fnf.FileNotFoundError(file_name)
        return instances
