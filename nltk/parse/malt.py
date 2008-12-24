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
from nltk import tag
from dependencygraph import DependencyGraph
from nltk.internals import find_binary


class MaltParser(object):

    def __init__(self, tagger=None):
        self.config_malt()
        self.mco = 'malt_temp'
        self._trained = False
        
        if tagger is not None:
            self.tagger = tagger
        else:
            self.tagger = tag.RegexpTagger(
            [(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),   # cardinal numbers
             (r'(The|the|A|a|An|an)$', 'AT'),   # articles
             (r'.*able$', 'JJ'),                # adjectives
             (r'.*ness$', 'NN'),                # nouns formed from adjectives
             (r'.*ly$', 'RB'),                  # adverbs
             (r'.*s$', 'NNS'),                  # plural nouns
             (r'.*ing$', 'VBG'),                # gerunds
             (r'.*ed$', 'VBD'),                 # past tense verbs
             (r'.*', 'NN')                      # nouns (default)
             ])
    
    def config_malt(self, bin=None, verbose=False):
        """
        Configure NLTK's interface to the C{malt} package.  This
        searches for a directory containing the malt jar
        
        @param bin: The full path to the C{malt} binary.  If not
            specified, then nltk will search the system for a C{malt}
            binary; and if one is not found, it will raise a
            C{LookupError} exception.
        @type bin: C{string}
        """
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

        # Find the malt binary.
        self._malt_bin = find_binary('malt.jar', bin,
            searchpath=malt_path, env_vars=['MALTPARSERHOME'],
            url='http://w3.msi.vxu.se/~jha/maltparser/index.html',
            verbose=verbose)
        self._malt_path = self._malt_bin.rsplit(os.sep,1)[0]
      
    def parse(self, sentence, verbose=False):
        """
        Use MaltParser to parse a sentence
        
        @param sentence: Input sentence to parse
        @type sentence: L{str}
        @return: C{DependencyGraph} the dependency graph representation of the sentence
        """
        if not self._malt_bin:
            raise Exception("MaltParser location is not configured.  Call config_malt() first.")
        if not self._trained:
            raise Exception("Parser has not been trained.  Call train() first.")
            
        input_file = os.path.join(tempfile.gettempdir(), 'malt_input.conll')
        output_file = os.path.join(tempfile.gettempdir(), 'malt_output.conll')
        
        execute_string = 'java -jar %s -w %s -c %s -i %s -o %s -m parse'
        if not verbose:
            execute_string += ' > ' + os.path.join(tempfile.gettempdir(), "malt.out")
        
        f = None
        try:
            f = open(input_file, 'w')
            for (i, (word,tag)) in enumerate(self.tagger.tag(sentence.split())):
                f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % 
                        (i+1, word, '_', tag, tag, '_', '0', 'a', '_', '_'))
            f.write('\n')
            f.close()
        
            cmd = ['java', '-jar %s' % self._malt_bin, '-w %s' % tempfile.gettempdir(), 
                   '-c %s' % self.mco, '-i %s' % input_file, '-o %s' % output_file, '-m parse']

            if not verbose: 
                cmd.append(' > %s' % (os.path.join(tempfile.gettempdir(), 'malt_parse.out')))
            os.system(' '.join(cmd))
            
            return DependencyGraph.load(output_file)
        finally:
            if f: f.close()
    
    def train(self, depgraphs, verbose=False):
        """
        Train MaltParser from a list of C{DependencyGraph}s
        
        @param depgraphs: C{list} of C{DependencyGraph}s for training input data
        """
        input_file = os.path.join(tempfile.gettempdir(),'malt_train.conll')

        f = None
        try:
            f = open(input_file, 'w')
            f.write('\n'.join([dg.to_conll(10) for dg in depgraphs]))
        finally:
            if f: f.close()
            
        self.train_from_file(input_file, verbose=verbose)

    def train_from_file(self, conll_file, verbose=False):
        """
        Train MaltParser from a file
        
        @param conll_file: C{str} for the filename of the training input data
        """
        if not self._malt_bin:
            raise Exception("MaltParser location is not configured.  Call config_malt() first.")

        cmd = ['java', '-jar %s' % self._malt_bin, '-w %s' % tempfile.gettempdir(), 
               '-c %s' % self.mco, '-i %s' % conll_file, '-m learn']
        
#        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
#                             stderr=subprocess.STDOUT,
#                             stdin=subprocess.PIPE)
#        (stdout, stderr) = p.communicate()
                
        if not verbose: 
            cmd.append(' > %s' % (os.path.join(tempfile.gettempdir(), 'malt_train.out')))
        malt_exit = os.system(' '.join(cmd))
        
        self._trained = True


def demo():
    dg1 = DependencyGraph("""1    John    _    NNP   _    _    2    SUBJ    _    _
                             2    sees    _    VB    _    _    0    ROOT    _    _
                             3    a       _    DT    _    _    4    SPEC    _    _
                             4    dog     _    NN    _    _    2    OBJ     _    _
                          """)
    dg2 = DependencyGraph("""1    John    _    NNP   _    _    2    SUBJ    _    _
                             2    walks   _    VB    _    _    0    ROOT    _    _
                          """)

    verbose = False
    
    maltParser = MaltParser()
    maltParser.train([dg1,dg2], verbose=verbose)

    print maltParser.parse('John sees Mary', verbose=verbose).deptree().pprint()
    print maltParser.parse('a man runs', verbose=verbose).deptree().pprint()
    
if __name__ == '__main__':
    demo()
