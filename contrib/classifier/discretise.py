# Natural Language Toolkit - Discretise
#  The command line entry point to discretisers
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import CommandLineInterface, split_ignore_space
from nltk_lite.contrib.classifier import instances as ins, discretisedattribute as da, cfile as f, numrange as r, format
from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv

import sys

class Discretise(CommandLineInterface):    
    def __init__(self):
        CommandLineInterface.__init__(self)

        a_help = "Selects the discretisation algorithm                 " \
               + "Options: UEW for Unsupervised Equal Width            " \
               + "         UEF for Unsupervised Equal Frequency        " \
               + "         NS for Naive Supervised                     " \
               + "         NS1 for Naive Supervised version 1          " \
               + "         NS2 for Naive Supervised version 2          " \
               + "         ES for Entropy Based Supervised             " \
               + "Default: UEW."
        t_help = "Training file for discretisation.                    "
        T_help = "Comma separated list of files to discterise based on " \
               + "the Training data."
        A_help = "Comma separated list of attribute indices.           "
        o_help = "Algorithm specific options                           " \
               + "UEW: Comma separated list of number of parts in which" \
               + "     each attribute should be split.                 "
        
        self.__algorithms = {'UEW':'unsupervised_equal_width', \
                             'UEF':'unsupervised_equal_frequency', \
                             'NS' :'naive_supervised', \
                             'NS1':'naive_supervised_v1', \
                             'NS2':'naive_supervised_v2', \
                             'ES' :'entropy_based_supervised'}
        self.add_option("-a", "--algorithm", dest="algorithm", type="choice", \
                        choices=self.__algorithms.keys(), default="UEW", help= a_help)
        self.add_option("-t", "--training-file", dest="training", type="string", help=t_help)
        self.add_option("-T", "--test-files", dest="test", type="string", help=T_help)
        self.add_option("-A", "--attributes", dest="attributes", type="string", help=A_help)
        self.add_option("-o", "--options", dest="options", type="string", help=o_help)
        
    def execute(self):
        algorithm = self.__algorithms[self.get_value('algorithm')]
        training = self.get_value('training')
        test = self.get_value('test')
        attributes = self.get_value('attributes')
        options = self.get_value('options')
        if algorithm is None or test is None or training is None or attributes is None or \
           ( not algorithm == self.__algorithms['NS'] and options is None): 
            self.error("Invalid arguments. One or more required arguments are not present.")
        self.invoke(training, test, attributes, options, algorithm)
        
    def invoke(self, training, test, attributes, options, algorithm):
        disc = Discretiser(training, test, attributes, options)
        files_written = getattr(disc, algorithm)()
        print 'The following files were created with discretised values...'
        for file_name in files_written:
            print file_name
    

class Discretiser:
    def __init__(self, path, test_files, attribute_indices, options = None):
        self.path = path
        self.training = format.C45_FORMAT.get_training_instances(path)
        self.attributes = format.C45_FORMAT.get_attributes(path)
        self.klass = format.C45_FORMAT.get_klass(path)
        file_names = split_ignore_space(test_files)
        self.instances = format.create_instances(file_names, format.C45_FORMAT)
        self.attribute_indices = as_integers('Attribute indices', attribute_indices)
        self.options = as_integers('Options', options)
        for option in self.options:
            if option == 0:
                raise inv.InvalidDataError('Option cannt be equal to zero.')
        self.subset = self.attributes.subset(self.attribute_indices)
        self.test_file_names = []
        for each in file_names:
            name, extension = f.name_extension(each)
            self.test_file_names.append(name)
                            
    def unsupervised_equal_width(self):
        ranges = self.training.value_ranges(self.subset)
        disc_attrs = self.discretised_attributes(ranges)
        return self.__discretise(disc_attrs)
    
    def __discretise(self, disc_attrs):
        files_written, suffix = [], self.get_suffix()
        self.training.discretise(disc_attrs)
        files_written.append(self.training.write_to_file(self.path, suffix, format.C45_FORMAT))
        for index in range(len(self.instances)):
            _instances = self.instances[index]
            _instances.discretise(disc_attrs)
            files_written.append(_instances.write_to_file(self.test_file_names[index], suffix, format.C45_FORMAT))
        self.attributes.discretise(disc_attrs)
        files_written.append(self.attributes.write_to_file(self.klass, self.path, suffix, format.C45_FORMAT))
        return files_written
    
    def unsupervised_equal_frequency(self):
        values_array = self.training.values_grouped_by_attribute(self.subset)
        disc_attrs = []
        for index in range(len(self.subset)):
            values = values_array[index]
            values.sort()
            attribute = self.subset[index] 
            ranges = ranges_from_chunks(get_chunks_with_frequency(values, self.options[index]))
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, ranges, attribute.index))
        return self.__discretise(disc_attrs)
    
    def naive_supervised(self):
        return self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive())

    def naive_supervised_v1(self):
        return self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive_v1(self.options[index]))

    def naive_supervised_v2(self):
        return self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive_v2(self.options[index]))
    
    def entropy_based_supervised(self):
        return self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_entropy_based_max_depth(self.options[index]))
    
    def __supervised_discretisation(self, action):
        disc_attrs = []
        for index in range(len(self.subset)):
            attribute = self.subset[index]
            breakpoints = self.training.supervised_breakpoints(attribute)
            action(breakpoints, index)
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, breakpoints.as_ranges(), attribute.index))
        return self.__discretise(disc_attrs)

    def discretised_attributes(self, ranges):
        discretised_attributes = []
        for index in range(len(self.options)):
            _range, width, attribute = ranges[index], self.options[index], self.subset[index]
            discretised_attributes.append(da.DiscretisedAttribute(attribute.name, _range.split(width), attribute.index))
        return discretised_attributes
            
    def get_suffix(self):
        indices_str = ''
        for index in self.attribute_indices:
            indices_str += '_' + str(index)
        return '-d' + indices_str

def get_chunks_with_frequency(values, freq):
    chunks = []
    while len(values) > 0:
        chunk = values[:freq]
        chunks.append(chunk)
        values = values[freq:]
        while len(values) > 0 and chunk[-1] == values[0]:
            values = values[1:]
    return chunks

def ranges_from_chunks(chunks):
    ranges = []
    for index in range(len(chunks) - 1):
        ranges.append(r.Range(chunks[index][0], chunks[index + 1][0]))
    ranges.append(r.Range(chunks[-1][0], chunks[-1][-1], True))
    return ranges

def as_integers(name, str_array):
    indices = []
    if str_array is not None:
        for element in str_array.split(','):
            try:
                indices.append(int(element.strip()))
            except ValueError:
                raise inv.InvalidDataError('Invalid Data. ' + name + ' should be integers.')
    return indices

if __name__ == "__main__":
    Discretise().run(sys.argv[1:])

