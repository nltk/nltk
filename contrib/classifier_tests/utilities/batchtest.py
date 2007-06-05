import os
import os.path
from nltk_lite.contrib.classifier import format as fmt, discretise as d, featureselect as f, classify as c
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
                if ext == fmt.C45_FORMAT.NAMES or ext == fmt.C45_FORMAT.DATA or ext == fmt.C45_FORMAT.TEST or ext == fmt.C45_FORMAT.GOLD:
                    data.add(dir_name + os.path.sep + file[:index])
        for each in data:
            process(each, log_path)
    
def process(path, log_path):
    attributes = fmt.C45_FORMAT.get_attributes(path)
    training = fmt.C45_FORMAT.get_training_instances(path)
    has_continuous = False
    disc_suffixes,filter_suffixes = [], []
    cross_validate = False
    if not os.path.exists(path + '.test') and not os.path.exists(path + '.gold'):
        cross_validate = True
    if attributes.has_continuous():
        has_continuous = True
        indices = attributes.continuous_attribute_indices()

        options = [len(training) / 10] * len(indices)
        disc = d.Discretise()
        params = ['-a', d.UNSUPERVISED_EQUAL_FREQUENCY, '-f', path, '-A', int_array_to_string(indices), '-o', int_array_to_string(options), '-l', log_path]
        print "Params " + str(params)
        disc.run(params)
        disc_suffixes.append(disc.get_suffix())

        options = [10] * len(indices)    
        disc = d.Discretise()
        params = ['-a', d.UNSUPERVISED_EQUAL_WIDTH , '-f', path, '-A', int_array_to_string(indices), '-o', int_array_to_string(options), '-l', log_path]
        print "Params " + str(params)
        disc.run(params)
        disc_suffixes.append(disc.get_suffix())
        
        disc = d.Discretise()
        params = ['-a', d.NAIVE_SUPERVISED, '-f', path, '-A', int_array_to_string(indices), '-l', log_path]
        print "Params " + str(params)
        disc.run(params)
        disc_suffixes.append(disc.get_suffix())

        for naive_mod_alg in [d.NAIVE_SUPERVISED_V1, d.NAIVE_SUPERVISED_V2]:
            disc = d.Discretise()
            params = ['-a', naive_mod_alg, '-f', path, '-A', int_array_to_string(indices), '-o', int_array_to_string(options), '-l', log_path]
            print "Params " + str(params)
            disc.run(params)
            disc_suffixes.append(disc.get_suffix())
    
    filter_inputs = ['']
    filter_inputs.extend(disc_suffixes)
    for each in filter_inputs:
        if has_continuous and each == '': continue
        for selection_criteria in [f.INFORMATION_GAIN, f.GAIN_RATIO]:
            feat_sel = f.FeatureSelect()
            params = ['-a', f.RANK, '-f', path + each, '-o', selection_criteria + ',' + str(get_number_of_filter_attributes(len(attributes))), '-l', log_path]
            print "Params " + str(params)
            feat_sel.run(params)
            filter_suffixes.append(each + feat_sel.get_suffix())
        
    suffixes = ['']
    suffixes.extend(disc_suffixes)
    suffixes.extend(filter_suffixes)
    
    for classification_alg in c.ALGORITHM_MAPPINGS.keys():
        wrapper_inputs = ['']
        wrapper_inputs.extend(disc_suffixes)
        if has_continuous and not c.ALGORITHM_MAPPINGS[classification_alg].can_handle_continuous_attributes():
            del wrapper_inputs[0]
        wrapper_suffixes = []
        
        for each in wrapper_inputs:
            for alg in [f.FORWARD_SELECTION, f.BACKWARD_ELIMINATION]:
                feat_sel = f.FeatureSelect()
                params = ['-a', alg, '-f', path + each, '-o', classification_alg + ',25,0.1', '-l', log_path]
                print "Params " + str(params)
                feat_sel.run(params)
                wrapper_suffixes.append(each + feat_sel.get_suffix())
            
        all = suffixes[:]
        if has_continuous and not c.ALGORITHM_MAPPINGS[classification_alg].can_handle_continuous_attributes():
            all.remove('')
        all.extend(wrapper_suffixes)
        for each in all:
            if cross_validate: 
                params = ['-a', classification_alg, '-f', path + each, '-l', log_path, '-c', 5]
                print "Params " + str(params)
                c.Classify().run(params)    
            else:
                params = ['-a', classification_alg, '-vf', path + each, '-l', log_path]
                print "Params " + str(params) 
                c.Classify().run(params)    
            

def get_number_of_filter_attributes(len_attrs):
    if len_attrs <= 10:
        return len_attrs * 2 / 3
    if len_attrs <= 20:
        return len_attrs / 2
    return 10 + (len_attrs - 20) / 8 
                
def int_array_to_string(int_array):
    str_array = []
    for each in int_array:
        str_array.append(str(each))
    return ','.join(str_array)

def delete_generated_files(path):
    to_be_deleted = []
    for (dir_name, dirs, files) in os.walk(path):
        for f in files:
            if f.find('-') != -1 and f.find('_') != -1:
                to_be_deleted.append(dir_name + os.path.sep + f)
    for each in to_be_deleted:
        os.remove(each)
                
if __name__ == "__main__":
    params = sys.argv[1:]
    if len(params) != 2:
        print("Usage: python batchtest.py dir_tree_path log_file")
    run(params[0], params[1])
