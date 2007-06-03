# Natural Language Toolkit - Feature Select
#  The command line entry point for feature selection
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import split_ignore_space
from nltk_lite.contrib.classifier import format, cfile, commandline as cl, attribute as attr, classify as cy
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv
import copy

import sys

a_help = "Selects the feature selection algorithm                 " \
       + "Options: RNK for Ranking(Filter method of Feature       " \
       + "                         Selection)                     " \
       + "         FS for Forward Selection(Wrapper)              " \
       + "         BE for Backward Eliminiation(Wrapper)          " \
       + "Default: RNK.                                           "
       
f_help = "Base name of attribute, klass, training, test and gold  " \
       + " files.                                                 "

t_help = "Base name of training file for feature selection.       "

T_help = "Base name of test file for feature selection.           "

g_help = "Base name of gold file for feature selection.           "

o_help = "Algorithm specific options                              " \
       + "                                                        " \
       + "For RNK based feature selection the options should      " \
       + "include the method to calculate the rank:               " \
       + "  IG: for Information gain                              " \
       + "  GR: for Gain ratio                                    " \
       + "followed by a number which indicates the number of      " \
       + "attributes which should be chosen.                      " \
       + "                                                        " \
       + "For FS and BE based feature selection the options should" \
       + "compulsorily include the induction algorithm as the first" \
       + "parameter. The second and third parameters are the fold " \
       + "and delta respectively. The default value of fold is 10." \
       + "The default value of delta is 0.                        " 

R_help = "Ranking algorithm.                                      "
INFORMATION_GAIN = 'IG'
GAIN_RATIO = 'GR'
OPTION_MAPPINGS = {INFORMATION_GAIN: 'information_gain', GAIN_RATIO: 'gain_ratio'}

RANK='RNK'
FORWARD_SELECTION='FS'
BACKWARD_ELIMINATION='BE'

ALGORITHM_MAPPINGS = {RANK:'by_rank', FORWARD_SELECTION:'forward_selection', BACKWARD_ELIMINATION:'backward_elimination'}
DEFAULT_FOLD=10
MIN_FOLD=2

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
        if self.algorithm == RANK and rank_options_invalid(self.options):
            self.error("Invalid options for Rank based Feature selection.")
        if (self.algorithm == FORWARD_SELECTION or self.algorithm == BACKWARD_ELIMINATION) and wrapper_options_invalid(self.options):
            self.error("Invalid options for Wrapper based Feature selection. Options Found: " + str(self.options))
        self.log_common_params('FeatureSelection')
        if self.log is not None: print >>self.log, 'Options: ' + str(self.options)
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
        
        files_written = self.write_to_file(self.get_suffix(), training, attributes, klass, test, gold, False)
        print >>self.log, 'The following files were created after feature selection...'
        for file_name in files_written:
            print >>self.log, file_name
            
    def get_suffix(self):
        if self.options is None: return '-' + self.algorithm
        suf = '-' + self.algorithm
        for option in self.options:
            suf += '_' + option.replace('.','-')
        return suf

class FeatureSelection:
    def __init__(self, training, attributes, klass, test, gold, options):
        self.training, self.attributes, self.klass, self.test, self.gold = training, attributes, klass, test, gold
        self.options = options
        
    def by_rank(self):
        if self.attributes.has_continuous():
            raise inv.InvalidDataError("Rank based feature selection cannot be performed on continuous attributes.")
        if rank_options_invalid(self.options):
            raise inv.InvalidDataError("Invalid options for Rank based Feature selection.")#Additional validation when not used from command prompt
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
    
    def forward_selection(self):
        if wrapper_options_invalid(self.options):
            raise inv.InvalidDataError("Invalid options for Forward Select Feature selection.")#Additional validation when not used from command prompt
        selected = self.__select_attributes(-1, [], self.attributes[:], self.get_delta())
        self.remove(self.invert_attribute_selection(selected))
        
    def backward_elimination(self):
        if wrapper_options_invalid(self.options):
            raise inv.InvalidDataError("Invalid options for Backward Select Feature selection.")
        fold = self.get_fold()
        avg_acc = self.avg_accuracy_by_cross_validation(self.training.cross_validation_datasets(fold), fold, self.attributes)
        selected = self.__eliminate_attributes(avg_acc, self.attributes[:], self.get_delta())
        self.remove(self.invert_attribute_selection(selected))
        
    def __eliminate_attributes(self, max, selected, delta):
        if selected is None or len(selected) == 0 or len(selected) == 1: return selected
        max_at_level, selections_with_max_acc, fold = -1, None, self.get_fold()
        datasets = self.training.cross_validation_datasets(fold)
        selected_for_iter = selected[:]
        for attribute in selected_for_iter:
            selected.remove(attribute)
            avg_accuracy = self.avg_accuracy_by_cross_validation(datasets, fold, attr.Attributes(selected))
            if avg_accuracy > max_at_level:
                max_at_level = avg_accuracy
                selections_with_max_acc = selected[:]
            selected.append(attribute)
        if max_at_level - max < delta: return selected
        return self.__eliminate_attributes(max_at_level, selections_with_max_acc, delta)
    
    def get_delta(self):
        if len(self.options) != 3:
            return 0
        return float(self.options[2])

    def invert_attribute_selection(self, selected):
        not_selected = []
        for attribute in self.attributes:
            if not selected.__contains__(attribute):
                not_selected.append(attribute)
        return not_selected
        
    def __select_attributes(self, max, selected, others, delta):
        if others is None or len(others) == 0: return selected
        max_at_level, attr_with_max_acc, fold = -1, None, self.get_fold()
        datasets = self.training.cross_validation_datasets(fold)
        for attribute in others:
            selected.append(attribute)
            avg_accuracy = self.avg_accuracy_by_cross_validation(datasets, fold, attr.Attributes(selected))
            if avg_accuracy > max_at_level:
                max_at_level = avg_accuracy
                attr_with_max_acc = attribute
            selected.remove(attribute)
        if max_at_level - max < delta: return selected
        selected.append(attr_with_max_acc)
        others.remove(attr_with_max_acc)
        return self.__select_attributes(max_at_level, selected, others, delta)
    
    def get_fold(self):
        if len(self.options) == 1:
            return DEFAULT_FOLD
        return int(self.options[1])

    def avg_accuracy_by_cross_validation(self, datasets, fold, attributes):
        total_accuracy = 0;
        for index in range(fold):
            training, gold = datasets[index]
            cm = cy.ALGORITHM_MAPPINGS[self.options[0]](training, attributes, self.klass, True).verify(gold)
            total_accuracy += cm.accuracy()
        return total_accuracy / len(datasets)
    
    def remove(self, attributes):
        self.training.remove_attributes(attributes)
        if self.test is not None: self.test.remove_attributes(attributes)
        if self.gold is not None: self.gold.remove_attributes(attributes)
        self.attributes.remove_attributes(attributes)

def rank_options_invalid(options):
    return len(options) != 2 or not OPTION_MAPPINGS.has_key(options[0]) or not options[1].isdigit()

def wrapper_options_invalid(options):
    return (len(options) < 1 or len(options) > 3) \
           or \
           (not cy.ALGORITHM_MAPPINGS.has_key(options[0]) \
                or \
                ( (len(options) == 2 or len(options) == 3) \
                     and \
                     (not options[1].isdigit() or int(options[1]) < MIN_FOLD)
                )
                or \
                len(options) == 3 and not isfloat(options[2])
           )

def isfloat(stringval):
    try:
        float(stringval)
        return True
    except (ValueError, TypeError), e: return False 
                        
def as_sets_array(array):
    sets = []
    for element in array:
        sets.append(set([element.index]))
    return sets
    

if __name__ == "__main__":
    FeatureSelect().run(sys.argv[1:])

