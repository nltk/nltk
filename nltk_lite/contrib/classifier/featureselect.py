# Natural Language Toolkit - Feature Select
#  The command line entry point for feature selection
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import CommandLineInterface, split_ignore_space
from nltk_lite.contrib.classifier import format, cfile
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

import sys

OPTIONS = {"IG": 'information_gain'}

class FeatureSelectCommandInterface(CommandLineInterface):
    def __init__(self):
        CommandLineInterface.__init__(self)

        a_help = "Selects the feature selection algorithm                 " \
               + "Options: RNK for Ranking(Filter based Feature Selection)" \
               + "Default: RNK."
        t_help = "Training file for feature selection.                    "
        T_help = "Comma separated list of files to discterise based on " \
               + "the Training data."
        o_help = "Algorithm specific options                              " \
               + "For rank based feature selection the options should     " \
               + "include the method to calculate the rank:               " \
               + "  IG: for Information gain                              " \
               + "followed by a number which indicates the number of      " \
               + "attributes which should be chosen"
        
        self.__algorithms = {'RNK':'by_rank'}
        self.add_option("-a", "--algorithm", dest="algorithm", type="choice", \
                        choices=self.__algorithms.keys(), default="RNK", help= a_help)
        self.add_option("-t", "--training-file", dest="training", type="string", help=t_help)
        self.add_option("-T", "--test-files", dest="test", type="string", help=T_help)
        self.add_option("-o", "--options", dest="options", type="string", help=o_help)

        
    def execute(self):
        algorithm = self.__algorithms[self.get_value('algorithm')]
        training = self.get_value('training')
        test = self.get_value('test')
        options = self.get_value('options')
        if algorithm is None or test is None or training is None or options is None: 
            self.error("Invalid arguments. One or more required arguments are not present.")
        options = split_ignore_space(options)
        if self.get_value('algorithm') == 'RNK' and (len(options) != 2 or not OPTIONS.has_key(options[0]) or not int(options[1])):
            self.error("Invalid options for Rank based feature selection. Options Found: " + str(options))
        self.invoke(training, test, options, algorithm)
        
    def invoke(self, training, test, options, algorithm):
        disc = FeatureSelect(training, test, options)
        files_written = getattr(disc, algorithm)()
        print 'The following files were created after feature selection...'
        for file_name in files_written:
            print file_name

class FeatureSelect:
    def __init__(self, training, test, options):
        self.training_path = training
        self.training = format.C45_FORMAT.get_training_instances(training)
        self.attributes = format.C45_FORMAT.get_attributes(training)
        self.klass = format.C45_FORMAT.get_klass(training)
        self.test_files = split_ignore_space(test)
        self.test = format.create_instances(self.test_files, format.C45_FORMAT)
        self.options = options
        
    def by_rank(self):
        if self.attributes.has_continuous_attributes():
            raise inv.InvalidDataError("Rank based feature selection cannot be performed on continuous attributes.")
        rem_attributes = self.find_attributes_by_ranking(OPTIONS[self.options[0]], int(self.options[1]))
        self.remove(rem_attributes)
        return self.write_files('-RNK-' + str(self.options[0]) + str(self.options[1]))
    
    def find_attributes_by_ranking(self, method, number):
        decision_stumps = self.attributes.empty_decision_stumps([], self.klass)
        for decision_stump in decision_stumps:
            self.training.for_each(lambda instance: decision_stump.update_count(instance))
        decision_stumps.sort(lambda x, y: cmp(getattr(x, method), getattr(y, method)))
        attributes_to_remove = []
        if number > len(decision_stumps): number = len(decision_stumps)
        to_remove = decision_stumps[number:]
        for stump in to_remove:
            attributes_to_remove.append(stump.attribute)
        return attributes_to_remove
    
    def remove(self, attributes):
        input_data = [self.attributes, self.training] + self.test
        for input in input_data:
            input.remove_attributes(attributes)
    
    def write_files(self, suffix):
        files_written = []
        files_written.append(self.attributes.write_to_file(self.klass, self.training_path, suffix, format.C45_FORMAT))
        files_written.append(self.training.write_to_file(self.training_path, suffix, format.C45_FORMAT))
        for index in range(len(self.test)):
            base_name, extension = cfile.name_extension(self.test_files[index])
            files_written.append(self.test[index].write_to_file(base_name, suffix, format.C45_FORMAT))
        return files_written
            
if __name__ == "__main__":
    FeatureSelectCommandInterface().run(sys.argv[1:])

