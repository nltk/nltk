# Natural Language Toolkit - Feature Select
#  The command line entry point for feature selection
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import split_ignore_space
from nltk_lite.contrib.classifier import format, cfile, commandline as cl
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

import sys

a_help = "Selects the feature selection algorithm                 " \
       + "Options: RNK for Ranking(Filter based Feature Selection)" \
       + "Default: RNK.                                           "
       
f_help = "Base name of attribute, klass, training, test and gold  " \
       + " files.                                                 "

t_help = "Base name of training file for feature selection.       "

T_help = "Base name of test file for feature selection.           "

g_help = "Base name of gold file for feature selection.           "

o_help = "Algorithm specific options                              " \
       + "For rank based feature selection the options should     " \
       + "include the method to calculate the rank:               " \
       + "  IG: for Information gain                              " \
       + "  GR: for Gain ratio                                    " \
       + "followed by a number which indicates the number of      " \
       + "attributes which should be chosen.                      "

OPTION_MAPPINGS = {'IG': 'information_gain', 'GR': 'gain_ratio'}

RANK='RNK'

ALGORITHM_MAPPINGS = {RANK:'by_rank'}

class FeatureSelect(cl.CommandLineInterface):
    def __init__(self):
        cl.CommandLineInterface.__init__(self, ALGORITHM_MAPPINGS.keys(), RANK, a_help, f_help, t_help, T_help, g_help)        
        self.add_option("-o", "--options", dest="options", type="string", help=o_help)
        
    def execute(self):
        cl.CommandLineInterface.execute(self)
        self.validate_basic_arguments_are_present()
        self.validate_files_arg_is_exclusive()
        if self.get_value('options') is None:
            self.required_arguments_not_present_error()
        self.options = split_ignore_space(self.get_value('options'))
        if self.algorithm == RANK and (len(self.options) != 2 or not OPTION_MAPPINGS.has_key(self.options[0]) or not int(self.options[1])):
            self.error("Invalid options for Rank based feature selection. Options Found: " + str(self.options))
        self.select_features_and_write_to_file()
        
    def select_features_and_write_to_file(self):
        ignore_missing = False
        #duplicate code and not tested!!
        if self.files is not None:
            self.training_path, self.test_path, self.gold_path = [self.files] * 3
            ignore_missing = True
        training, attributes, klass, test, gold = self.get_instances(self.training_path, self.test_path, self.gold_path, ignore_missing)

        feature_sel = FeatureSelection(training, attributes, klass, test, gold, self.options)
        getattr(feature_sel, ALGORITHM_MAPPINGS[self.algorithm])()
        
        files_written = self.write_to_file(self.get_suffix(), training, attributes, klass, test, gold)
        print 'The following files were created after feature selection...'
        for file_name in files_written:
            print file_name
            
    def get_suffix(self):
        if self.options is None: return '-' + self.algorithm
        suf = '-' + self.algorithm
        for option in self.options:
            suf += '_' + option
        return suf

class FeatureSelection:
    def __init__(self, training, attributes, klass, test, gold, options):
        self.training, self.attributes, self.klass, self.test, self.gold = training, attributes, klass, test, gold
        self.options = options
        
    def by_rank(self):
        if self.attributes.has_continuous_attributes():
            raise inv.InvalidDataError("Rank based feature selection cannot be performed on continuous attributes.")
        if len(self.options) != 2 or not OPTION_MAPPINGS.has_key(self.options[0]) or not int(self.options[1]):
            raise inv.InvalidDataError("Invalid options for Rank based feature selection.")#Additional validation when not used from command prompt
        rem_attributes = self.find_attributes_by_ranking(OPTION_MAPPINGS[self.options[0]], int(self.options[1]))
        self.remove(rem_attributes)
    
    def find_attributes_by_ranking(self, method, number):
        decision_stumps = self.attributes.empty_decision_stumps([], self.klass)
        for decision_stump in decision_stumps:
            for instance in self.training:
                decision_stump.update_count(instance)
        decision_stumps.sort(lambda x, y: cmp(getattr(x, method)(), getattr(y, method)()))
        
        if number > len(decision_stumps): number = len(decision_stumps)
        to_remove, attributes_to_remove = decision_stumps[:number * -1], []
        for stump in to_remove:
            attributes_to_remove.append(stump.attribute)
        return attributes_to_remove
    
    def remove(self, attributes):
        self.training.remove_attributes(attributes)
        if self.test is not None: self.test.remove_attributes(attributes)
        if self.gold is not None: self.gold.remove_attributes(attributes)
        self.attributes.remove_attributes(attributes)
                
if __name__ == "__main__":
    FeatureSelect().run(sys.argv[1:])

