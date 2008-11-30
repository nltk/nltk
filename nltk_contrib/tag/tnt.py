# Natural Language Toolkit: Interface to TnT 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile
from nltk import tokenize
from nltk.internals import find_binary

_tnt_bin = None

def config_tnt(bin=None, verbose=False):
    """
    Configure the location of TnT Executable
    
    @param path: Path to the TnT executable
    @type path: C{str}
    """
    
    try:
        if _tnt_bin:
            return _tnt_bin
    except UnboundLocalError:
        pass
    
    # Find the tnt binary.
    tnt_bin = find_binary('tnt', bin,
        searchpath=tnt_search, env_vars=['TNTHOME'],
        url='http://www.coli.uni-saarland.de/~thorsten/tnt/',
        verbose=verbose)
    
    _tnt_bin = tnt_bin
    return _tnt_bin

tnt_search = ['.',
              '/usr/lib/tnt',
              '/usr/local/bin',
              '/usr/local/bin/tnt']

def pos_tag(sentence, model_path=None, verbose=False):
    """
    Use TnT to parse a sentence
    
    @param sentence: Input sentence to parse
    @type sentence: L{str}
    @return: C{DepGraph} the dependency graph representation of the sentence
    """
    
    tnt_bin = config_tnt(verbose=verbose)
    
    if not model_path:
        model_path = '%s/models/wsj' % tnt_bin[:-4]
        
    input_file =  '%s/tnt_in.txt' % tnt_bin[:-4]
    output_file = '%s/tnt_out.txt' % tempfile.gettempdir()
    
    execute_string = '%s %s %s > %s'
    if not verbose:
        execute_string += ' 2> %s/tnt.out' % tempfile.gettempdir()
    
    tagged_words = []
    
    f = None
    try:
        if verbose: 
            print 'Begin input file creation' 
            print 'input_file=%s' % input_file

        f = open(input_file, 'w')
        words = tokenize.WhitespaceTokenizer().tokenize(sentence)
        for word in words:
            f.write('%s\n' % word)
        f.write('\n')
        f.close()
        if verbose: print 'End input file creation'
    
        if verbose:
            print 'tnt_bin=%s' % tnt_bin 
            print 'model_path=%s' % model_path
            print 'output_file=%s' % output_file
    
        execute_string = execute_string % (tnt_bin, model_path, input_file, output_file)
        
        if verbose: 
            print 'execute_string=%s' % execute_string
        
        if verbose: print 'Begin tagging'
        tnt_exit = os.system(execute_string)
        if verbose: print 'End tagging (exit code=%s)' % tnt_exit
        
        f = open(output_file, 'r')
        lines = f.readlines()
        f.close()

        tagged_words = []
        tokenizer = tokenize.WhitespaceTokenizer()
        for line in lines:
            if not line.startswith('%%'):
                tokens = tokenizer.tokenize(line.strip())
                if len(tokens) == 2:
                    tagged_words.append((tokens[0], tokens[1]))
                
        if verbose:
            for tag in tagged_words:
                print tag

    finally:
        if f: f.close()

    return tagged_words


if __name__ == '__main__':
#    train(True)

    pos_tag('John sees Mary', verbose=True)
    
