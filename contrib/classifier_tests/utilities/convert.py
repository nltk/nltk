import re
from nltk.contrib.classifier import format
import os, os.path

def convert_and_shift(file_path, ext, suffix = 'conv', sep = ' '):
    """
    converts elements separated by a blank space into comma separated data
    also changes the position of the class element from the first element 
    to the last element
    """
    lines = []
    f = open(file_path, 'r')
    for line in f:        
        words = line.split(sep)
        words[-1] = words[-1].strip()
        words = words[1:] + [words[0]]
        lines.append(','.join(words))
    f.close()
    ext_dot_index = file_path.rindex('.')
    if ext_dot_index == -1:
        base_name = file_path
    else:
        base_name = file_path[:ext_dot_index]
    f = open((base_name + suffix) + '.' + ext, 'w')
    for line in lines:
        f.write(line + '\n')
    f.close()    
    
def values(file_path, index, sep = " "):
    """
    returns a comma separated list of all values that an 
    element at index 'index' can take in a file at 'file_path'
    """
    values = set([])
    f = open(file_path, 'r')
    for line in f:        
        words = line.split(sep)
        if not index < len(words):
            print "Warning! omitting line " + str(line)
            continue
        values.add(words[index])
    return ','.join(values)
    
def convert(path):
    """
    converts elements separated by a blank space into comma separated data
    """
    converted = []
    f = open(path, 'r')
    for l in f:
        elements = l.split()
        converted.append(','.join(elements))
    f.close()
    ind = path.rfind('.')
    if ind == -1: ind = len(path)
    nf = open(path[:ind] + 'conv' + path[ind:], 'w')
    for l in converted:print >>nf, l
    nf.close()
    
def convert_log_to_csv(path):
    f = open(path)
    separator = '-' * 40
    classifications = []
    obj = None
    for each in f:
        if each.find(separator) != -1:
            if obj != None and obj.operation == 'Classification':
                classifications.append(obj)
            obj = LogEntry()            
        else:
            parts = each.split(":")
            if len(parts) < 2: continue
            name = parts[0].strip()
            name = name.lower()
            name = re.sub('-', '_', name)
            if len(parts) > 2: value = parts[1:]
            else: value = parts[1].strip()
            setattr(obj, name, value)
    
    csvf = open(path + '.csv', 'w')
    for each in classifications:
        print >>csvf, each.algorithm + ',' + each.training + ',' + each.test + ',' + each.gold + ',' + each.accuracy + ',' + each.f_score

def create_CV_datasets(path, fold):
    training = format.C45_FORMAT.get_training_instances(path)
    datasets = training.cross_validation_datasets(fold)
    slash = path.rindex(os.path.sep)
    parent_path = path[:slash]
    name = path[slash + 1:]
    for i in range(len(datasets)):
        os.makedirs(parent_path + os.path.sep + str(i + 1))
        format.C45_FORMAT.write_training_to_file(datasets[i][0], parent_path + os.path.sep + str(i + 1) + os.path.sep + name)
        format.C45_FORMAT.write_gold_to_file(datasets[i][1], parent_path + os.path.sep + str(i + 1) + os.path.sep + name)
    
class LogEntry:
    pass

    
