# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT


import re
from nltk_contrib.classifier import format, discretise as ds, featureselect as fs, classify, util
import os, os.path

DISC_METHODS = [ds.UNSUPERVISED_EQUAL_WIDTH, ds.UNSUPERVISED_EQUAL_FREQUENCY, ds.NAIVE_SUPERVISED, ds.NAIVE_SUPERVISED_V1, ds.NAIVE_SUPERVISED_V2, ds.ENTROPY_BASED_SUPERVISED]
FS_METHODS = [fs.RANK, fs.FORWARD_SELECTION, fs.BACKWARD_ELIMINATION]
FS_OPTIONS = [fs.INFORMATION_GAIN, fs.GAIN_RATIO]
CLASSIFIERS = [classify.ZERO_R, classify.ONE_R, classify.DECISION_TREE, classify.NAIVE_BAYES, classify.IB1]

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
    converted = [','.join(l.split()) for l in f]
    f.close()
    ind = path.rfind('.')
    if ind == -1: ind = len(path)
    nf = open(path[:ind] + 'conv' + path[ind:], 'w')
    for l in converted:print >>nf, l
    nf.close()
    
def convert_log_to_csv(path):
    classifications = get_classification_log_entries(path)
    
    csvf = open(path + '.csv', 'w')
    for each in classifications:
        print >>csvf, each.algorithm + ',' + each.training + ',' + each.test + ',' + each.gold + ',' + each.accuracy + ',' + each.f_score

def get_classification_log_entries(path):
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
    return classifications

def convert_log_to_tex_tables(path):
    classifications = get_classification_log_entries(path)
    
    datasets = {}
    for each in classifications:
        dataset = get_dataset_name(each.training)
        if not dataset in datasets:
            datasets[dataset] = {}
            
        if not each.algorithm in datasets[dataset]:
            datasets[dataset][each.algorithm] = {classify.ACCURACY:{}, classify.F_SCORE:{}}
        pp = get_preprocessing(each.training)
        datasets[dataset][each.algorithm][classify.ACCURACY][pp] = float(each.accuracy)
        datasets[dataset][each.algorithm][classify.F_SCORE][pp] = float(each.f_score)
    
    cols = [str(None)]
    cols.extend(DISC_METHODS) 
    
    rows = [str(None)] + combine_methods(fs.RANK, FS_OPTIONS)
    
    accuracy_tables = []
    f_score_tables = []
    
    for dataset in datasets:
        accuracy_table = get_tex_table_header(dataset, classify.ACCURACY, cols)
        f_score_table = get_tex_table_header(dataset, classify.F_SCORE, cols)
        
        for alg in CLASSIFIERS:
            rows += [fs.FORWARD_SELECTION + '_' + alg, fs.BACKWARD_ELIMINATION + '_' + alg]
            accuracy_table += ' \\multirow{' + str(len(rows)) + '}{*}{' + alg + '}'
            f_score_table += ' \\multirow{' + str(len(rows)) + '}{*}{' + alg + '}'
            for index in range(len(rows)):
                sel = rows[index]
                accuracies, fscores = [], []

                for disc in cols:
                    if (disc, sel) in datasets[dataset][alg][classify.ACCURACY]:
                        if float == type(datasets[dataset][alg][classify.ACCURACY][(disc, sel)]) or int == type(datasets[dataset][alg][classify.ACCURACY][(disc, sel)]):
                            acc = datasets[dataset][alg][classify.ACCURACY][(disc, sel)]
                            fsc = datasets[dataset][alg][classify.F_SCORE][(disc, sel)]
                            accuracies.append('%.4f' % acc)
                            fscores.append('%.4f' % fsc)
                        else:
                            accuracies.append(datasets[dataset][alg][classify.ACCURACY][(disc, sel)])
                            fscores.append(datasets[dataset][alg][classify.F_SCORE][(disc, sel)])
                    else:
                        accuracies.append('')
                        fscores.append('')
                accuracy_table += ' & ' + get_fs_display_name(sel) + ' & ' + ' & '.join(accuracies) + '\\\\ \n'
                f_score_table += ' & ' + get_fs_display_name(sel) + ' & ' + ' & '.join(fscores) + '\\\\ \n'
                
            accuracy_table += '\\hline \n'
            f_score_table += '\\hline \n'            
            rows.remove(fs.FORWARD_SELECTION + '_' + alg)
            rows.remove(fs.BACKWARD_ELIMINATION + '_' + alg)

        
        accuracy_table += get_tex_table_footer()
        f_score_table += get_tex_table_footer()
        accuracy_tables.append(accuracy_table)
        f_score_tables.append(f_score_table)
    allrows = rows + combine_methods(fs.FORWARD_SELECTION, CLASSIFIERS) + combine_methods(fs.BACKWARD_ELIMINATION, CLASSIFIERS)
    
    mean_accuracy_tables = []
    for dataset in datasets:
        mean_accuracy_table = get_mean_tex_table_header(dataset, "Mean Accuracy", cols)   
        for row in allrows:
            mean_accuracy_table += get_fs_display_name(sel)
            for column in cols:
                stat_list = util.StatList()
                for alg in CLASSIFIERS:
                    if (column, row) in datasets[dataset][alg][classify.ACCURACY]:
                        val = datasets[dataset][alg][classify.ACCURACY][(column, row)]
                        if float == type(val) or int == type(val):
                            stat_list.append(val)
                mean_accuracy_table += ' & %.4f' %stat_list.mean()
            mean_accuracy_table += '\\\\ \n'
        mean_accuracy_table += '\\hline'
        mean_accuracy_table += get_tex_table_footer()
        mean_accuracy_tables.append(mean_accuracy_table)        
        
    mean_datasets = ''
    mean_datasets = get_tex_table_header("All Datasets", "Mean Accuracy", cols)   
    test_classifiers = CLASSIFIERS[:]
    test_classifiers.remove(classify.ZERO_R)
    for alg in test_classifiers:
        rows += [fs.FORWARD_SELECTION + '_' + alg, fs.BACKWARD_ELIMINATION + '_' + alg]
        mean_datasets += '\\hline \\multirow{' + str(len(rows) * 2) + '}{*}{' + alg + '}'
        for row in rows:
            mean_datasets += ' & \\multirow{2}{*}{' + get_fs_display_name(row) + '}'
            stat_list_col = {}
            for column in cols:
                stat_list = util.StatList()
                for dataset in datasets:
                    if (column, row) in datasets[dataset][alg][classify.ACCURACY]:
                        val = datasets[dataset][alg][classify.ACCURACY][(column, row)]
                        if float == type(val) or int == type(val):
                            if row.find(fs.FORWARD_SELECTION) != -1:
                                oner_row = fs.FORWARD_SELECTION + '_' + classify.ZERO_R
                            elif row.find(fs.BACKWARD_ELIMINATION) != -1:
                                oner_row = fs.BACKWARD_ELIMINATION + '_' + classify.ZERO_R
                            else:
                                oner_row = row
                            stat_list.append(val - datasets[dataset][classify.ZERO_R][classify.ACCURACY][(column, oner_row)])
                stat_list_col[column] = stat_list
            for column in cols:
                mean_datasets += ' & %.4f' %stat_list_col[column].mean()
            mean_datasets += '\\\\ \n &'
            for column in cols:
                mean_datasets += ' & ($\\pm$ %.4f)' %stat_list_col[column].std_dev()            
            mean_datasets += '\\\\ \n'
        rows.remove(fs.FORWARD_SELECTION + '_' + alg)
        rows.remove(fs.BACKWARD_ELIMINATION + '_' + alg)

        mean_datasets += '\\hline'
    mean_datasets += get_tex_table_footer()
        
    texf = open(path + '-acc.tex', 'w')
    for table in accuracy_tables:
        print >>texf, table
    texf = open(path + '-fs.tex', 'w')
    for table in f_score_tables:
        print >>texf, table
    texf = open(path + '-macc.tex', 'w')
    for table in mean_accuracy_tables:
        print >>texf, table
    texf = open(path + '-mdatasets.tex', 'w')
    print >>texf, mean_datasets

def get_stat_lists(cols):
    return dict([(each, util.StatList()) for each in cols])        

def get_fs_display_name(name):
    if name.find('_') == -1:
        return name
    parts = name.split('_')
    if parts[0] == fs.FORWARD_SELECTION or parts[0] == fs.BACKWARD_ELIMINATION:
        return parts[0]
    return ' '.join(parts)
        
def get_tex_table_header(dataset, measure, cols):
    return '\\begin{table*}\n' + \
        '\\centering\n' + \
        '\\caption{' + dataset.capitalize() + ' - ' + measure.capitalize() +'}\n' + \
        '\\label{'+ dataset + '_' + measure +'}\n' + \
        '\\begin{tabular}{cc|' + 'c' * len(cols) + '}\n' + \
        '\\hline \\textbf{Algorithm} & \\textbf{Feature selection} & \\multicolumn{7}{|c}{\\textbf{Discretization}}\\\\ \n' + \
        ' & & ' + ' & '.join(cols) + ' \\\\ \n' + \
        '\\hline'

def get_mean_tex_table_header(dataset, measure, cols):
    return '\\begin{table*}\n' + \
        '\\centering\n' + \
        '\\caption{' + dataset.capitalize() + ' - ' + measure.capitalize() +'}\n' + \
        '\\label{'+ dataset + '_' + measure +'}\n' + \
        '\\begin{tabular}{c|' + 'c' * len(cols) + '}\n' + \
        '\\hline \\textbf{Feature selection} & \\multicolumn{7}{|c}{\\textbf{Discretization}}\\\\ \n' + \
        ' & ' + ' & '.join(cols) + ' \\\\ \n' + \
        '\\hline'


def get_tex_table_footer():
    return '\\end{tabular} \n' + \
        '\\end{table*} \n'

def get_dataset_name(name):
    filename = name.split('-d_')[0]
    filename = filename.split('-f_')[0]
    return os.path.basename(filename)   

def get_preprocessing(name):
    discn = get_pp(name, 'd')
    fsn = get_pp(name, 'f')
    return (discn, fsn)

def combine_methods(base, options):
    return [base + '_' + each for each in options]

def get_pp(name, pp_method):
    parts = name.split(get_dataset_name(name))[-1].split('-')
    i = 1
    while (i < len(parts)):
        if parts[i].find(pp_method) != -1:
            elements = parts[i].split('_')
            to_be_removed = []
            for index in range(len(elements)):
                each = elements[index]
                if not DISC_METHODS.__contains__(each) and not FS_METHODS.__contains__(each) and not FS_OPTIONS.__contains__(each) and not CLASSIFIERS.__contains__(each):
                    to_be_removed.append(index)
            to_be_removed.sort()
            to_be_removed.reverse()
            for each in to_be_removed:
                elements.__delitem__(each)
            return '_'.join(elements)
        i+=1
    return str(None)

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

if __name__ == "__main__":
    convert_log_to_tex_tables('/home/sumukh/changedlog')


    
