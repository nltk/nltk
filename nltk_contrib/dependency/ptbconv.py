# Natural Language Toolkit: ptbconv.py
#
# Author: Dan Garrette <dhgarrette@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
This module serves as an interface with the ptbconv tool found at 
http://www.jaist.ac.jp/~h-yamada/.

For this interface to work correctly, the environment variable "PTBCONV" should
be set to the location of the ptbconv binary.
"""


import subprocess
import math
from nltk.internals import find_binary
import os

OUTPUT_FORMAT = '%s\t%s\t_\t%s\t_\t_\t%s\t%s\t_\t_\n'

def convert(num, format='D', tofile=False, verbose=False):
    """
    @param num: the number of the treebank file
    @param format: D = dependency list
                   V = dependency tree
    @param tofile: write the output to a file?
    """
    stdout = _run_ptbconv(num, format, verbose)
        
    if tofile and format == 'D':
        _write_file(num, stdout, verbose)
    else:
        return stdout


def _write_file(num, dep_list_str, verbose=False):
    output_filename = reduce(os.path.join, 
                             [_treebank_path(), 'dep', 
                              'wsj_%04d.dep.untagged' % num])
    output_file = open(output_filename, 'w')
    
    i = 1
    for line in dep_list_str.split('\n'):
        if not line:
            output_file.write('\n')
            i = 1
        else:
            word, pos, head = line.split()
            
            if head == '-1': head = 0
            rel = _get_relation(word, pos, head)
            output_file.write(OUTPUT_FORMAT % (i, word, pos, head, rel))
            i += 1
    
def _get_relation(word, pos, head):
    if head == '0':
        return 'ROOT'
    if pos == 'JJ':
        return 'MOD'
    if pos == 'DT':
        return 'SPEC'
    if pos == '.' or pos == ',':
        return 'PUNCT'
    
    return '<rel>'

def _run_ptbconv(num, format='D', verbose=False):
    bin = find_binary('ptbconv', 
                      env_vars=['PTBCONV'],
                      url='http://www.jaist.ac.jp/~h-yamada/',
                      verbose=False)
    
    input_filename = reduce(os.path.join, 
                        [_treebank_path(), 'combined', 'wsj_%04d.mrg' % num])
    
    cmd = [bin, '-'+format]
    p = subprocess.Popen(cmd, 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=open(input_filename))
    (stdout, stderr) = p.communicate()
    
    if verbose:
        print stderr.strip()
        
    return stdout


def _treebank_path():
    return reduce(os.path.join, 
                  [os.environ['NLTK_DATA'], 'corpora', 'treebank'])

def convert_all():
    for i in xrange(199):
        print '%s:' % (i+1),
        convert(i+1, 'D', True, True)

if __name__ == '__main__':
    print convert(1, 'D')
    