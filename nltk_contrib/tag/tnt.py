# Natural Language Toolkit: Interface to TnT 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
from nltk import tokenize

def config_tnt(path=None, verbose=False):
    """
    Configure the location of TnT Executable
    
    @param path: Path to the TnT executable
    @type path: C{str}
    """
    
    tnt_path = None
    
    tnt_search = ['.',
                  '/usr/local/bin',
                  '/usr/local/bin/tnt',
                  'c:\\cygwin\\usr\\local\\bin',
                  'c:\\cygwin\\usr\\local\\bin\\tnt']

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = tnt_search
        if 'TNTHOME' in os.environ:
            searchpath.insert(0, os.environ['TNTHOME'])

    for path in searchpath:
        jar = os.path.join(path, 'tnt.exe')
        if os.path.exists(jar):
            tnt_path = path
            if verbose:
                print '[Found TnT: %s]' % jar
            return tnt_path
  
    if tnt_path is None:
        raise LookupError("Unable to find TnT executable in '%s'\n" 
            "Use 'config_tnt(path=<path>) '," 
            " or set the TNTHOME environment variable to a valid path." % join(searchpath)) 

def pos_tag(sentence, model_path=None, verbose=False):
    """
    Use TnT to parse a sentence
    
    @param sentence: Input sentence to parse
    @type sentence: L{str}
    @return: C{DepGraph} the dependency graph representation of the sentence
    """
    
    tnt_path = config_tnt(verbose=verbose)
    exe_path = '%s/tnt.exe' % tnt_path
    
    if not model_path:
        model_path = '%s/models/wsj' % tnt_path
        
    tag_path = '%s/nltk_contrib/tag' % os.environ['PYTHONPATH']
    input_file =  '%s/in.txt' % tag_path
    output_file = '%s/out.txt' % tag_path
    
    win_path = os.path.exists('c:\\')
    if win_path:
        full_model_path = '`cygpath -w %s`' % model_path
        full_tag_path = '`cygpath -w %s`' % tag_path
        full_input_file =  '`cygpath -w %s`' % input_file
        full_output_file = '`cygpath -w %s`' % output_file
    else:
        full_model_path = model_path
        full_tag_path = tag_path
        full_input_file =  input_file
        full_output_file = output_file
    
    execute_string = '%s %s %s > %s'
    if not verbose:
        execute_string += ' 2> %s/tnt.out' % tag_path
    
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
            print 'exe_path=%s' % exe_path 
            print 'full_tag_path=%s' % full_tag_path
            print 'full_model_path=%s' % full_model_path
            print 'full_input_file=%s' % full_input_file
            print 'full_output_file=%s' % full_output_file
    
        execute_string = execute_string % (exe_path, full_model_path, full_input_file, full_output_file)
        
        if verbose: 
            print 'execute_string=%s' % execute_string
        
        if verbose: print 'Begin tagging'
        tnt_exit = os.system(execute_string)
        if verbose: print 'End tagging (exit code=%s)' % tnt_exit
        
        f = open(output_file, 'r')
        lines = f.readlines()
        f.close()

        tagged_words = []
        tokenizer = tokenize.TabTokenizer()
        for line in lines:
            if not line.startswith('%%'):
                tokens = tokenizer.tokenize(line.strip())
                if len(tokens) > 1:
                    tagged_words.append((tokens[0], tokens[3]))
                
        if verbose:
            for tag in tagged_words:
                print tag

    finally:
        if f: f.close()

    return tagged_words


if __name__ == '__main__':
#    train(True)

    pos_tag('John sees Mary', verbose=True)
    