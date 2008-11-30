# Natural Language Toolkit: Interface to MaltParser 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile
import subprocess
import glob
from operator import add

from nltk import data
from nltk import tokenize
from nltk_contrib.dependency import DepGraph, util
from nltk_contrib.tag import tnt
from nltk.internals import find_binary

_malt_bin = None

def config_malt(bin=None, verbose=False):
    """
    Configure NLTK's interface to the C{malt} package.  This
    searches for a directory containing the malt jar
    
    @param bin: The full path to the C{malt} binary.  If not
        specified, then nltk will search the system for a C{malt}
        binary; and if one is not found, it will raise a
        C{LookupError} exception.
    @type bin: C{string}
    """
    try:
        if _malt_bin:
            return _malt_bin
    except UnboundLocalError:
        pass
    
    # Find the malt binary.
    malt_bin = find_binary('malt.jar', bin,
        searchpath=malt_path, env_vars=['MALTPARSERHOME'],
        url='http://w3.msi.vxu.se/~jha/maltparser/index.html',
        verbose=verbose)
    
    _malt_bin = malt_bin
    return _malt_bin
  
#: A list of directories that should be searched for the malt
#: executables.  This list is used by L{config_malt} when searching
#: for the malt executables.
_malt_path = ['.',
             '/usr/lib/malt-1*',
             '/usr/local/bin',
             '/usr/local/malt-1*',
             '/usr/local/bin/malt-1*',
             '/usr/local/malt-1*',
             '/usr/local/share/malt-1*']

# Expand wildcards in _malt_path:
malt_path = reduce(add, map(glob.glob, _malt_path))

######################################################################
#{ Interface to Binaries
######################################################################

def parse(sentence, mco='temp', tagger='tnt', stem=True, verbose=False):
    """
    Use MaltParser to parse a sentence
    
    @param sentence: Input sentence to parse
    @type sentence: L{str}
    @param tagger: The tagger to use.  Use 'tnt' for the TnT tagger, or 'nltk' to
    simply use the treebank that comes with NLTK 
    @type tagger: L{str}
    @return: C{DepGraph} the dependency graph representation of the sentence
    """
    
    _malt_bin = config_malt(verbose=verbose)
    
    input_file = os.path.join(tempfile.gettempdir(), "malt_input")
    output_file = os.path.join(tempfile.gettempdir(), "malt_output")
    
    execute_string = 'java -jar %s -w %s -c %s -i %s -o %s -m parse'
    if not verbose:
        execute_string += ' > ' + os.path.join(tempfile.gettempdir(), "malt.out")
    
    depgraph = None
    
    f = None
    try:
        if verbose: 
            print 'Begin input file creation' 
            print 'input_file=%s' % input_file

        f = open(input_file, 'w')
        
        if tagger == 'tnt':
            tagged_words = tnt.pos_tag(sentence)
        elif tagger == 'nltk':
            tagged_words = pos_tag(sentence)
        else:
            raise AssertionError, 'tagger \'%s\' is not recognized' % tagger
        
        assert tagged_words, 'tagged_words is empty'
        if verbose: print 'tagged_words =', tagged_words
        
        for (i, word) in enumerate(tagged_words):
            #f.write('%s\t%s\t%s\t%s%s\n' % (i+1, words[i], '\t_'*4, '0', '\t_'*3))
            f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % 
                    (i+1, word[0], '_', word[1], word[1], '_', '0', 'a', '_', '_'))
        f.write('\n')
        f.close()
        if verbose: print 'End input file creation'
    
        if verbose:
            print '_malt_bin=%s' % _malt_bin 
            print 'mco_file=%s/%s.mco' % (os.environ['MALTPARSERHOME'],mco)
            print 'input_file=%s' % input_file
            print 'output_file=%s' % output_file
    
        execute_string = execute_string % (_malt_bin, os.environ['MALTPARSERHOME'], mco, input_file, output_file)
        
        if verbose: 
            print 'execute_string=%s' % execute_string
        
        if verbose: print 'Begin parsing'
        malt_exit = os.system(execute_string)
        if verbose: print 'End parsing (exit code=%s)' % malt_exit
        
        f = open(output_file, 'r')
        return util.conll_to_depgraph(f.read(), stem, verbose)
    
    finally:
        if f: f.close()

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

def train(mco='temp', conll='temp_train.conll', verbose=False):
    """
    Train MaltParser
    
    @param mco: C{str} for the mco output file.  i.e. if mco='temp', the file will be 'temp.mco'
    @param conll: C{str} the training input data
    @param sentence: Input sentence to parse
    """
    _malt_bin = config_malt(verbose=verbose)
    
    input_file = data.find(os.path.join('grammars', conll))

    execute_string = 'java -jar %s -w %s -c %s -i %s -m learn'
    if not verbose:
        execute_string += ' > %s/malt.out' % tempfile.gettempdir()
    
    depgraph = None
    
    if verbose:
        print 'malt_bin=%s' % _malt_bin 
        print 'mco_file=%s/%s.mco' % (os.environ['MALTPARSERHOME'], mco)
        print 'input_file=%s' % input_file

    execute_string = execute_string % (_malt_bin, os.environ['MALTPARSERHOME'], mco, input_file)
    
    if verbose: 
        print 'execute_string=%s' % execute_string
    
    if verbose: print 'Begin Training'
    malt_exit = os.system(execute_string)
    if verbose: print 'End Training (exit code=%s)' % malt_exit

def demo():
    mco = 'glue'
    train(mco, 'glue_train.conll', verbose=True)

    parse('John sees Mary', mco, verbose=True)
    parse('a man runs', mco, verbose=True)
    
if __name__ == '__main__':
    demo()
