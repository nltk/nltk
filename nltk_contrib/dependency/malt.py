# Natural Language Toolkit: Interface to MaltParser 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
from nltk import tokenize
from nltk_contrib.dependency import DepGraph

def config_malt(path=None, verbose=False):
    """
    Configure the location of MaltParser Executable
    
    @param path: Path to the MaltParser executable
    @type path: C{str}
    """
    
    malt_path = None
    
    malt_search = ['.',
                       '/usr/local/bin',
                       '/usr/local/bin/malt-1.0.2',
                       '/usr/local/malt-1.0.2',
                       '/usr/local/share/malt-1.0.2',
                       'c:\\cygwin\\usr\\local\\bin\\malt-1.0.2']

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = malt_search
        if 'MALTHOME' in os.environ:
            searchpath.insert(0, os.environ['MALTHOME'])

    for path in searchpath:
        jar = os.path.join(path, 'malt.jar')
        if os.path.exists(jar):
            malt_path = path
            if verbose:
                print '[Found MaltParser: %s]' % jar
            return malt_path
  
    if malt_path is None:
        raise LookupError("Unable to find MaltParser executable in '%s'\n" 
            "Use 'config_malt(path=<path>) '," 
            " or set the MALTHOME environment variable to a valid path." % join(searchpath)) 

def parse(sentence, verbose=False):
    """
    Use MaltParser to parse a sentence
    
    @param sentence: Input sentence to parse
    @type sentence: L{str}
    @return: C{DepGraph} the dependency graph representation of the sentence
    """
    
    malt_path = config_malt(verbose=verbose)
    jar_path = '%s/malt.jar' % malt_path
    
    mco_file = 'glue'
    dep_path = '%s/nltk_contrib/dependency' % os.environ['PYTHONPATH']
    input_file =  '%s/in.conll' % dep_path
    output_file = '%s/out.conll' % dep_path
    
    win_path = os.path.exists('c:\\')
    if win_path:
        full_jar_path = '`cygpath -w %s`' % jar_path
        full_dep_path = '`cygpath -w %s`' % dep_path
        full_input_file =  '`cygpath -w %s`' % input_file
        full_output_file = '`cygpath -w %s`' % output_file
    else:
        full_jar_path = jar_path
        full_dep_path = dep_path
        full_input_file =  input_file
        full_output_file = output_file
    
    execute_string = 'java -jar %s -w %s -c %s -i %s -o %s -m parse'
    if not verbose:
        execute_string += ' > %s/malt.out' % dep_path
    
    depgraph = None
    
    f = None
    try:
        if verbose: 
            print 'Begin input file creation' 
            print 'input_file=%s' % input_file

        f = open(input_file, 'w')
        tagged_words = pos_tag(sentence)
        for i in range(len(tagged_words)):
            #f.write('%s\t%s\t%s\t%s%s\n' % (i+1, words[i], '\t_'*4, '0', '\t_'*3))
            f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % 
                    (i+1, tagged_words[i][0], '_', tagged_words[i][1], tagged_words[i][1], '_', '0', 'a', '_', '_'))
        f.write('\n')
        f.close()
        if verbose: print 'End input file creation'
    
        if verbose:
            print 'full_jar_path=%s' % full_jar_path 
            print 'full_dep_path=%s' % full_dep_path
            print 'full_mco_file=%s' % mco_file
            print 'full_input_file=%s' % full_input_file
            print 'full_output_file=%s' % full_output_file
    
        execute_string = execute_string % (full_jar_path, full_dep_path, mco_file, full_input_file, full_output_file)
        
        if verbose: 
            print 'execute_string=%s' % execute_string
        
        if verbose: print 'Begin parsing'
        malt_exit = os.system(execute_string)
        if verbose: print 'End parsing (exit code=%s)' % malt_exit
        
        f = open(output_file, 'r')
        lines = f.readlines()
        f.close()

        tokenizer = tokenize.TabTokenizer()
        depgraph_input = ''
        for line in lines:
            tokens = tokenizer.tokenize(line.strip())
            if len(tokens) > 1:
                depgraph_input += '%s\t%s\t%s\t%s\n' % (tokens[1], tokens[3], tokens[6], tokens[7])

        if verbose:
            print 'Begin DepGraph creation'
            print 'depgraph_input=\n%s' % depgraph_input
        depgraph = DepGraph().read(depgraph_input)
        if verbose:
            print 'End DepGraph creation'
            
    finally:
        if f: f.close()

    return depgraph

def pos_tag(sentence, verbose=False):
    from nltk.corpus import treebank
    treebankDict = {}
    for (word,tag) in treebank.tagged_words():
        treebankDict[word] = tag
    
    words = tokenize.WhitespaceTokenizer().tokenize(sentence)
    tagged_words = []
    for word in words:
        try:
            tag = {'a'     : 'ex_quant',
                   'an'    : 'ex_quant',
                   'every' : 'univ_quant'
                   }[word.lower()]
        except:
            try:
                tag = treebankDict[word]
            except:
                raise KeyError('\'%s\' is not in the Part-of-Speech lookup' % word )
        tagged_words.append((word, tag))
    return tagged_words

def train(verbose=False):
    """
    Train MaltParser
    
    @param sentence: Input sentence to parse
    @type sentence: L{str}
    @return: C{DepGraph} the dependency graph representation of the sentence
    """
    
    malt_path = config_malt(verbose=verbose)
    jar_path = '%s/malt.jar' % malt_path
    
    mco_file = 'glue'
    dep_path = '%s/nltk_contrib/dependency' % os.environ['PYTHONPATH']
    input_file =  '%s/glue_train.conll' % dep_path
    
    win_path = os.path.exists('c:\\')
    if win_path:
        full_jar_path = '`cygpath -w %s`' % jar_path
        full_dep_path = '`cygpath -w %s`' % dep_path
        full_input_file =  '`cygpath -w %s`' % input_file
    else:
        full_jar_path = jar_path
        full_dep_path = dep_path
        full_input_file =  input_file
    
    execute_string = 'java -jar %s -w %s -c %s -i %s -m learn'
    if not verbose:
        execute_string += ' > %s/malt.out' % dep_path
    
    depgraph = None
    
    if verbose:
        print 'full_jar_path=%s' % full_jar_path 
        print 'full_dep_path=%s' % full_dep_path
        print 'full_mco_file=%s' % mco_file
        print 'full_input_file=%s' % full_input_file

    execute_string = execute_string % (full_jar_path, full_dep_path, mco_file, full_input_file)
    
    if verbose: 
        print 'execute_string=%s' % execute_string
    
    if verbose: print 'Begin Training'
    malt_exit = os.system(execute_string)
    if verbose: print 'End Training (exit code=%s)' % malt_exit


if __name__ == '__main__':
    train(True)

    parse('John sees Mary', verbose=True)
    parse('a man runs', verbose=True)
    