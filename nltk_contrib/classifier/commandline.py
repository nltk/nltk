# Natural Language Toolkit CommandLine
#     understands the command line interaction
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from optparse import OptionParser
from nltk_contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
from nltk_contrib.classifier import format
import time

D_help = "Used to specify the data format.                      " \
        + "Options: C45 for C4.5 format.                        " \
        + "Default: C45.                                        "
l_help = "Used to specify the log file.                         "


ALGORITHM = 'algorithm'
FILES = 'files'
TRAINING = 'training'
TEST = 'test'
GOLD = 'gold'
DATA_FORMAT = 'data_format'
LOG_FILE = 'log_file'
OPTIONS = 'options'

C45_FORMAT = 'c45' 

DATA_FORMAT_MAPPINGS = {C45_FORMAT: format.c45}

class CommandLineInterface(OptionParser):
    def __init__(self, alg_choices, alg_default, a_help, f_help, t_help, T_help, g_help, o_help):
        OptionParser.__init__(self)
        self.add_option("-a", "--algorithm", dest=ALGORITHM, type="choice", \
                        choices=alg_choices, default=alg_default, help= a_help)
        self.add_option("-f", "--files", dest=FILES, type="string", help=f_help)
        self.add_option("-t", "--training-file", dest=TRAINING, type="string", help=t_help)
        self.add_option("-T", "--test-file", dest=TEST, type="string", help=T_help)
        self.add_option("-g", "--gold-file", dest=GOLD, type="string", help=g_help)
        
        self.add_option("-D", "--data-format", dest=DATA_FORMAT, type="choice", choices=DATA_FORMAT_MAPPINGS.keys(), \
                default=C45_FORMAT, help=D_help)
        self.add_option("-l", "--log-file", dest=LOG_FILE, type="string", help=l_help)
        self.add_option("-o", "--options", dest=OPTIONS, type="string", help=o_help)
        
    def get_value(self, name):
        return self.values.ensure_value(name, None)
    
    def parse(self, args):
        """
        method to aid testing
        """
        self.parse_args(args, None)

    def execute(self):
        """
        Stores values from arguments which are common to all command line interfaces
        """
        self.algorithm = self.get_value(ALGORITHM)
        self.files = self.get_value(FILES)
        self.training_path = self.get_value(TRAINING)
        self.test_path = self.get_value(TEST)
        self.gold_path = self.get_value(GOLD)
        self.options = self.get_value(OPTIONS)
        self.data_format = DATA_FORMAT_MAPPINGS[self.get_value(DATA_FORMAT)]
        log_file = self.get_value(LOG_FILE)
        self.log = None
        if log_file is not None:
            self.log = open(log_file, 'a')
            print >>self.log, '-' * 40
            print >>self.log, 'DateTime: ' + time.strftime('%c', time.localtime())

    def run(self, args):
        """
        Main method which delegates all the work
        """
        self.parse(args)
        self.execute()
        if self.log is not None: self.log.close()
        
    def validate_basic_arguments_are_present(self):
        if self.algorithm is None or self.files is None and self.training_path is None : 
            self.required_arguments_not_present_error()
            
    def validate_files_arg_is_exclusive(self):
        if self.files is not None and (self.training_path is not None or self.test_path is not None or self.gold_path is not None):
            self.error("Invalid arguments. The files argument cannot exist with training, test or gold arguments.")

    def get_instances(self, training_path, test_path, gold_path, ignore_missing = False):
        test = gold = None
        training = self.data_format.training(training_path)
        attributes, klass = self.data_format.metadata(training_path)
        test = self.__get_instance(self.data_format.test, test_path, ignore_missing)
        gold = self.__get_instance(self.data_format.gold, gold_path, ignore_missing)
        return (training, attributes, klass, test, gold)
    
    def __get_instance(self, method, path, ignore_if_missing):
        if path is not None:
            if ignore_if_missing:
                try:
                    return method(path)
                except fnf.FileNotFoundError:
                    return None
            return method(path)
        return None

    def required_arguments_not_present_error(self):
        self.error("Invalid arguments. One or more required arguments are not present.")
        
    def write_to_file(self, suffix, training, attributes, klass, test, gold, include_classification = True):
        files_written = []
        files_written.append(self.data_format.write_training(training, self.training_path + suffix))
        if test is not None: files_written.append(self.data_format.write_test(test, self.test_path + suffix, include_classification))
        if gold is not None: files_written.append(self.data_format.write_gold(gold, self.gold_path + suffix, include_classification))
        files_written.append(self.data_format.write_metadata(attributes, klass, self.training_path + suffix))
        return files_written
    
    def log_common_params(self, name):
        if self.log is not None: 
            print >>self.log, 'Operation: ' + name
            print >>self.log, '\nAlgorithm: ' + str(self.algorithm) + '\nTraining: ' + str(self.training_path) + \
                    '\nTest: ' + str(self.test_path) + '\nGold: ' + str(self.gold_path) + '\nOptions: ' + str(self.options)
            
            
    def log_created_files(self, files_names, message):
        if self.log is None:
            print message
        else:
            print >>self.log, "NumberOfFilesCreated: " + str(len(files_names))
        count = 0
        for file_name in files_names:
            if self.log is None:
                print file_name
            else:
                print >>self.log, "CreatedFile" + str(count) + ": " + file_name
            count += 1


def as_integers(name, com_str):
    indices = []
    if com_str is not None:
        for element in com_str.split(','):
            try:
                indices.append(int(element.strip()))
            except ValueError:
                raise inv.InvalidDataError('Invalid Data. ' + name + ' should contain integers.')
    return indices

