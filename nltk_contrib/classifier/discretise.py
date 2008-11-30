# Natural Language Toolkit - Discretise
#  The command line entry point to discretisers
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier import split_ignore_space
from nltk_contrib.classifier import instances as ins, discretisedattribute as da, cfile as f, numrange as r, format, commandline as cl, util
from nltk_contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
import sys

a_help = "Selects the discretisation algorithm                 " \
       + "Options: UEW for Unsupervised Equal Width            " \
       + "         UEF for Unsupervised Equal Frequency        " \
       + "         NS for Naive Supervised                     " \
       + "         NS1 for Naive Supervised version 1          " \
       + "         NS2 for Naive Supervised version 2          " \
       + "         ES for Entropy Based Supervised             " \
       + "Default: UEW."

f_help = "Base name of attribute, klass, training, test and gold" \
       + " files.                                              "

t_help = "Base name of training file for discretisation.       "

T_help = "Base name of test file to be discretised.            "

g_help = "Base name of gold file to be discretised.            "

A_help = "Comma separated list of attribute indices           " \
       + "Index numbering starts from 0 and not 1.                         "

o_help = "Algorithm specific options                           " \
       + "UEW: Comma separated list of number of parts in which" \
       + "     each attribute should be split.                 "

UNSUPERVISED_EQUAL_WIDTH = 'UEW'
UNSUPERVISED_EQUAL_FREQUENCY = 'UEF'
NAIVE_SUPERVISED = 'NS'
NAIVE_SUPERVISED_V1 = 'NS1'
NAIVE_SUPERVISED_V2 = 'NS2'
ENTROPY_BASED_SUPERVISED = 'ES'

ALGORITHM_MAPPINGS = {UNSUPERVISED_EQUAL_WIDTH : 'unsupervised_equal_width', \
                     UNSUPERVISED_EQUAL_FREQUENCY : 'unsupervised_equal_frequency', \
                     NAIVE_SUPERVISED : 'naive_supervised', \
                     NAIVE_SUPERVISED_V1 : 'naive_supervised_v1', \
                     NAIVE_SUPERVISED_V2 : 'naive_supervised_v2', \
                     ENTROPY_BASED_SUPERVISED : 'entropy_based_supervised'}


class Discretise(cl.CommandLineInterface):    
    def __init__(self):
        cl.CommandLineInterface.__init__(self, ALGORITHM_MAPPINGS.keys(), UNSUPERVISED_EQUAL_WIDTH, a_help, f_help, t_help, T_help, g_help, o_help)
        self.add_option("-A", "--attributes", dest="attributes", type="string", help=A_help)
        
    def execute(self):
        cl.CommandLineInterface.execute(self)
        self.attributes_indices = self.get_value('attributes')
        self.validate_basic_arguments_are_present()
        self.validate_files_arg_is_exclusive()
        
        if not self.algorithm == NAIVE_SUPERVISED and self.options is None: 
            self.error("Invalid arguments. One or more required arguments are not present.")
        self.discretise_and_write_to_file()
        
    def discretise_and_write_to_file(self):
        ignore_missing = False
        #duplicate code and not tested!!
        if self.files is not None:
            self.training_path, self.test_path, self.gold_path = [self.files] * 3
            ignore_missing = True
        training, attributes, klass, test, gold = self.get_instances(self.training_path, self.test_path, self.gold_path, ignore_missing)
        self.log_common_params('Discretisation')    
        disc = Discretiser(training, attributes, klass, test, gold, cl.as_integers('Attribute indices', self.attributes_indices), cl.as_integers('Options', self.options))
        getattr(disc, ALGORITHM_MAPPINGS[self.algorithm])()
        files_written = self.write_to_file(self.get_suffix(), training, attributes, klass, test, gold, False)
        self.log_created_files(files_written, 'The following files were created with discretised values...')
            
    def get_suffix(self):
        indices_str = ''
        indices = self.attributes_indices.split(',')
        for index in indices:
            indices_str += '_' + str(index.strip())
        return '-d' + '_' + self.algorithm + indices_str

class Discretiser:
    def __init__(self, training, attributes, klass, test, gold, attribute_indices, options = None):
        """
        Initializes the discretiser object
        self.subset contains the attributes which have to be discretised
        """
        self.training, self.attributes, self.klass, self.test, self.gold = training, attributes, klass, test, gold
        self.attribute_indices, self.options = attribute_indices, options
        self.__validate_attribute_indices()
        self.__validate_options()
        self.subset = self.attributes.subset(self.attribute_indices)

    def __validate_options(self):
        if self.options is None: return
        for option in self.options:
            if option == 0:
                raise inv.InvalidDataError('Option cannot be equal to zero.')

    def __validate_attribute_indices(self):
        for index in self.attribute_indices:
            if index < 0 or index >= len(self.attributes):
                raise inv.InvalidDataError('Attribute indices should be between 0 and ' + str(len(self.attributes) - 1) + ' both inclusive, but found ' + str(index))
            
    def unsupervised_equal_width(self):
        ranges = self.training.value_ranges(self.subset)
        disc_attrs = self.discretised_attributes(ranges)
        self.__discretise(disc_attrs)
    
    def __discretise(self, disc_attrs):
        self.training.discretise(disc_attrs)
        if self.test is not None: self.test.discretise(disc_attrs)
        if self.gold is not None: self.gold.discretise(disc_attrs)
        self.attributes.discretise(disc_attrs)
    
    def unsupervised_equal_frequency(self):
        values_array = self.training.values_grouped_by_attribute(self.subset)
        disc_attrs = []
        for index in range(len(self.subset)):
            values = values_array[index]
            values.sort()
            attribute = self.subset[index] 
            ranges = ranges_from_chunks(get_chunks_with_frequency(values, self.options[index]))
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, ranges, attribute.index))
        self.__discretise(disc_attrs)
    
    def naive_supervised(self):
        self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive())

    def naive_supervised_v1(self):
        self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive_v1(self.options[index]))

    def naive_supervised_v2(self):
        self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_naive_v2(self.options[index]))
    
    def entropy_based_supervised(self):
        self.__supervised_discretisation(lambda breakpoints, index: breakpoints.find_entropy_based_max_depth(self.options[index]))
    
    def __supervised_discretisation(self, action):
        disc_attrs = []
        for index in range(len(self.subset)):
            attribute = self.subset[index]
            breakpoints = self.training.supervised_breakpoints(attribute)
            action(breakpoints, index)
            disc_attrs.append(da.DiscretisedAttribute(attribute.name, breakpoints.as_ranges(), attribute.index))
        self.__discretise(disc_attrs)

    def discretised_attributes(self, ranges):
        discretised_attributes = []
        for index in range(len(self.options)):
            _range, width, attribute = ranges[index], self.options[index], self.subset[index]
            discretised_attributes.append(da.DiscretisedAttribute(attribute.name, _range.split(width), attribute.index))
        return discretised_attributes
            
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
    if len(chunks) > 0: prev = chunks[0][0]
    for index in range(len(chunks) - 1):
        mid = float(chunks[index][-1] + chunks[index + 1][0]) / 2
        ranges.append(r.Range(prev, mid))
        prev = mid
    ranges.append(r.Range(prev, chunks[-1][-1], True))
    return ranges

def create_and_run(algorithm, path, indices, log_path, options):
    disc = Discretise()
    params = ['-a', algorithm, '-f', path, '-A', util.int_array_to_string(indices_string)]
    if options is not None:
        params.extend(['-o', options])
    if log_path is not None:
        params.extend(['-l', log_path])
    print "Params " + str(params)
    disc.run(params)
    return disc.get_suffix()

def batch_run(path, indices, log_path, options):
    created_file_suffixes = []
    for each in options:
        suffix = self.create_and_run(each, path, indices, log_path, options[each])
        created_file_suffixes.append(suffix)
    return created_file_suffixes

if __name__ == "__main__":
    Discretise().run(sys.argv[1:])

