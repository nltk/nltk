# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT


import os
import os.path
from nltk_contrib.classifier import format as fmt, discretise as d, featureselect as f, classify as c, util
import sys

def run(root_path, log_path):
    print('in run')
    for dir_name, dirs, files in os.walk(root_path):
        data = set([])
        print('Dir name ' + str(dir_name) + ' dirs ' + str(dirs) + ' files ' + str(files))
        for file in files:
            index = file.rfind('.')
            if index != -1:
                ext = file[index + 1:]
                if ext == fmt.c45.NAMES or ext == fmt.c45.DATA or ext == fmt.c45.TEST or ext == fmt.c45.GOLD:
                    data.add(dir_name + os.path.sep + file[:index])
        for each in data:
            process(each, log_path)
    
def process(path, log_path):
    attributes, klass = fmt.c45.metadata(path)
    training = fmt.c45.training(path)

    disc_suffixes, filter_inputs = [], []
    has_continuous = attributes.has_continuous()
    
    if has_continuous:
        indices = attributes.continuous_attribute_indices()
        
        uef_options = to_str_array(len(training) / 10, len(indices))
        uew_options = to_str_array(10, len(indices))
        ns_mod_options = to_str_array(len(training) / 15, len(indices))
        en_options = to_str_array(3, len(indices))# 3 will result in 8 classes(closest to 10)
        
        disc_suffixes = d.batch_run(path, indices, log_path, {d.UNSUPERVISED_EQUAL_FREQUENCY: uef_options, 
                                              d.UNSUPERVISED_EQUAL_WIDTH: uew_options,
                                              d.NAIVE_SUPERVISED: None,
                                              d.NAIVE_SUPERVISED_V1: ns_mod_options,
                                              d.NAIVE_SUPERVISED_V2: ns_mod_options,
                                              d.ENTROPY_BASED_SUPERVISED: en_options})
        filter_inputs = ['']
    filter_inputs.extend(disc_suffixes)
    filter_suffixes = f.batch_filter_select(path, filter_inputs, get_number_of_filter_attributes(len(attributes)), log_path, has_continuous)
        
    suffixes = ['']
    suffixes.extend(disc_suffixes)
    suffixes.extend(filter_suffixes)
    
    for algorithm in c.ALL_ALGORITHMS:
        wrapper_inputs, all = [''], suffixes[:]
        wrapper_inputs.extend(disc_suffixes)
        if has_continuous and not c.ALGORITHM_MAPPINGS[algorithm].can_handle_continuous_attributes():
            del wrapper_inputs[0]
            all.remove('')
        wrapper_suffixes = f.batch_wrapper_select(path, wrapper_inputs, algorithm, 25, 0.1, log_path)
        all.extend(wrapper_suffixes)
        
        for suffix in all:
            params = ['-a', algorithm, '-f', path + suffix, '-l', log_path, '-c', 5]
            print "Params " + str(params)
            c.Classify().run(params)    
            
def to_str_array(value, times):
    return util.int_array_to_string([value] * times)
        
def get_number_of_filter_attributes(len_attrs):
    if len_attrs <= 10:
        return len_attrs * 2 / 3
    if len_attrs <= 20:
        return len_attrs / 2
    return 10 + (len_attrs - 20) / 8 
                
def delete_generated_files(path):
    to_be_deleted = []
    for (dir_name, dirs, files) in os.walk(path):
        for f in files:
            if f.find('-') != -1 and f.find('_') != -1:
                to_be_deleted.append(dir_name + os.path.sep + f)
    for each in to_be_deleted:
        os.remove(each)
                
if __name__ == "__main__":
    resp = 0
    while(resp != 1 and resp != 2):
        try:
            resp = int(raw_input("Select one of following options:\n1. Run all tests\n2. Delete generated files\n"))
        except ValueError:
            pass
    if resp == 1:
        dir_tree_path = raw_input("Enter directory tree path")
        log_file = raw_input("Enter log file")
        run(dir_tree_path, log_file)
    elif resp == 2:
        dir_path = raw_input("Enter directory path")
        delete_generated_files(dir_path)
