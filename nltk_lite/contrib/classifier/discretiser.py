# Natural Language Toolkit - Discretiser
#  Capable of dicretising numeric values into dicrete attributes
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, attributes as attrs, discretisedattribute as da, cfile as f, numrange as r
from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv

class Discretiser:
    def __init__(self, path, test_files, attribute_indices, options = None):
        self.training = ins.TrainingInstances(path)
        self.attributes = attrs.Attributes(path)
        self.instances = self.create_instances(self.__test_files(test_files))
        self.attribute_indices = self.__as_integers('Attribute indices', attribute_indices)
        self.options = self.__as_integers('Options', options)
        for option in self.options:
            if option == 0:
                raise inv.InvalidDataError('Option cannt be equal to zero.')
        
    def __test_files(self, file_names):
        _file_names = []
        for name in file_names.split(','):
            _file_names.append(name.strip())
        return _file_names
    
    def __as_integers(self, name, str_array):
        indices = []
        if str_array is not None:
            for element in str_array.split(','):
                try:
                    indices.append(int(element.strip()))
                except ValueError:
                    raise inv.InvalidDataError('Invalid Data. ' + name + ' should be integers.')
        return indices
                    
    def unsupervised_equal_width(self):
        attrs = self.attributes.subset(self.attribute_indices)
        ranges = self.training.as_ranges(attrs)
        disc_attrs = self.discretised_attributes(ranges)
        return self.__discretise(disc_attrs)
    
    def __discretise(self, disc_attrs):
        to_be_discretised = [self.attributes, self.training] + self.instances
        files_written, suffix = [], self.get_suffix()
        for each in to_be_discretised:
            each.discretise(disc_attrs)
            files_written.append(each.write_to_file(suffix))
        return files_written
    
    def unsupervised_equal_frequency(self):
        attrs = self.attributes.subset(self.attribute_indices)
        values_array = self.training.values_grouped_by_attribute(attrs)
        disc_attrs = []
        for index in range(len(values_array)):
            values = values_array[index]
            values.sort()
            attribute = attrs[index] 
            chunks = self.get_chunks_with_frequency(values, self.options[index])
            ranges = self.ranges_from_chunks(chunks)
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, ranges, attribute.index))
        return self.__discretise(disc_attrs)
    
    def naive_supervised(self):
        attrs = self.attributes.subset(self.attribute_indices)
        disc_attrs = []
        for attribute in attrs:
            self.training.sort_by(attribute)
            breakpoints = self.training.breakpoints_in_class_membership()
            attr_values = self.training.attribute_values(attribute)
            for index in range(len(breakpoints)):
                while self.__same_values_on_either_side_of_breakpoint(attr_values, breakpoints[index]) and not (index == len(breakpoints) - 1 or breakpoints[index] >= breakpoints[index + 1]):
                    breakpoints[index] += 1
                if index != len(breakpoints) - 1 and breakpoints[index] >= breakpoints[index + 1]:
                    breakpoints.remove(breakpoints[index])
            ranges = self.ranges_from_breakpoints(attr_values, breakpoints)
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, ranges, attribute.index))
        return self.__discretise(disc_attrs)
            
    def __same_values_on_either_side_of_breakpoint(self, values, breakpoint):
        if breakpoint == len(values) - 1:
            return False
        return values[breakpoint] == values[breakpoint + 1]
                
    def ranges_from_breakpoints(self, attr_values, breakpoints):
        ranges, lower = [], attr_values[0]
        for breakpoint in breakpoints:
            mid = (attr_values[breakpoint] + attr_values[breakpoint + 1]) / 2.0
            ranges.append(r.Range(lower, mid))
            lower = mid
        ranges.append(r.Range(lower, attr_values[-1], True))
        return ranges

    def get_chunks_with_frequency(self, values, freq):
        chunks = []
        while len(values) > 0:
            chunk = values[:freq]
            chunks.append(chunk)
            values = values[freq:]
            while len(values) > 0 and chunk[-1] == values[0]:
                values = values[1:]
        return chunks

    def ranges_from_chunks(self, chunks):
        lower = chunks[0][0]
        ranges = []
        for index in range(len(chunks) - 1):
            ranges.append(r.Range(chunks[index][0], chunks[index + 1][0]))
        ranges.append(r.Range(chunks[-1][0], chunks[-1][-1], True))
        return ranges

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
    
    def get_suffix(self):
        indices_str = ''
        for index in self.attribute_indices:
            indices_str+= '_' + str(index)
        return '-d' + indices_str
