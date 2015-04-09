# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2015 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function

import os
import fnmatch
import tempfile
import glob
from operator import add
from functools import reduce
import subprocess
import fileinput

from nltk.tag import RegexpTagger
from nltk.tokenize import word_tokenize
from nltk.data import ZipFilePathPointer
from nltk.internals import find_binary

from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph

def find_jars_within_path(path_to_jars):
    return [os.path.join(root, filename) 
            for root, dirnames, filenames in os.walk(path_to_jars) 
            for filename in fnmatch.filter(filenames, '*.jar')]

def create_regex_tagger():
    cardinals =     (r'^-?[0-9]+(.[0-9]+)?$', 'CD') # cardinal numbers
    articles =      (r'(The|the|A|a|An|an)$', 'AT') # articles
    adjectives =    (r'.*able$', 'JJ') # adjectives
    nounfromadj =   (r'.*ness$', 'NN') # nouns formed from adjectives
    adverbs =       (r'.*ly$', 'RB') # adverbs
    pluralnouns =   (r'.*s$', 'NNS')# plural nouns
    gerunds =       (r'.*ing$', 'VBG') # gerunds
    pastverbs =     (r'.*ed$', 'VBD') # past tense verbs
    nouns =         (r'.*', 'NN') # nouns (default)
    return RegexpTagger([cardinals, articles, adjectives, 
                         nounfromadj, adverbs, pluralnouns, 
                         gerunds, pastverbs, nouns])

def taggedsent_to_conll(sentences):
    """
    A module to convert the a POS tagged document stream 
    (i.e. list of list of tuples) and yield lines in CONLL format. 
    This module yields one line per word and two newlines for end of sentence. 
    
    >>> from nltk import word_tokenize, sent_tokenize
    >>> text = "This is a foobar sentence. Is that right?"
    >>> sentences = [word_tokenize(sent) for sent in sent_tokenize(text)]
    >>> for line in taggedsent_to_conll(sentences):
    ...     print(line, end="")
    1    This    _    DT    DT    _    0    a    _    _
    2    is    _    VBZ    VBZ    _    0    a    _    _
    3    a    _    DT    DT    _    0    a    _    _
    4    foobar    _    NN    NN    _    0    a    _    _
    5    sentence    _    NN    NN    _    0    a    _    _
    6    .    _    .    .    _    0    a    _    _
    
    
    1    Is    _    VBZ    VBZ    _    0    a    _    _
    2    that    _    IN    IN    _    0    a    _    _
    3    right    _    JJ    JJ    _    0    a    _    _
    4    ?    _    .    .    _    0    a    _    _
    """
    for sentence in sentences:
        for (i, (word, tag)) in enumerate(sentence, start=1):
            input_str = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
            % (i, word, '_', tag, tag, '_', '0', 'a', '_', '_')
            yield input_str.encode("utf8")
        yield b'\n\n'
            
class MaltParser(ParserI):
    def __init__(self, path_to_maltparser, model=None, tagger=None, 
                 working_dir=None, additional_java_args=[]):
        """
        An interface for parsing with the Malt Parser.
        
        :param model: The name of the pre-trained model with .mco file 
        extension. If provided, training will not be required.
        (see http://www.maltparser.org/mco/mco.html and 
        see http://www.patful.com/chalk/node/185)
        :type mco: str
        :param tagger: The tagger used to POS tag the raw string before 
        formatting to CONLL format. It should behave like `nltk.pos_tag`
        :type tagger: function
        :param additional_java_args: This is the additional Java arguments that 
        one can use when calling Maltparser, usually this is the heapsize 
        limits, e.g. `additional_java_args=['-Xmx1024m']`
        (see http://goo.gl/mpDBvQ)
        :type additional_java_args: list
        :param path_to_maltparser: The path to the maltparser directory that 
        contains the maltparser-1.x.jar
        :type path_to_malt_binary: str
        """
        # Collects all the jar files found in the MaltParser distribution.
        self.malt_jars = find_jars_within_path(path_to_maltparser)
        # Initialize additional java arguments.
        self.additional_java_args = additional_java_args
        
        # Set the working_dir parameters i.e. `-w` from MaltParser's option.
        self.working_dir = tempfile.gettempdir() \
                        if working_dir is None  else working_dir
        
        # Initialize POS tagger.
        if tagger is not None:
            self.tagger = tagger
        else: # Use a default Regex Tagger if none specified.
            self.tagger = create_regex_tagger()
        
        # Initialize maltparser model.
        self.mco = 'malt_temp.mco' if model is None else model
        self._trained = False if self.mco == 'malt_temp' else True
            
    def tagged_parse_sents(self, sentences, verbose=False):
        """
        Use MaltParser to parse multiple sentences. Takes multiple sentences
        where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentence: list(list(tuple(str, str)))
        :return: iter(iter(``DependencyGraph``)) the dependency graph 
        representation of each sentence
        """
        if not self._trained:
            raise Exception("Parser has not been trained. Call train() first.")
        
        input_file = tempfile.NamedTemporaryFile(prefix='malt_input.conll',  
                                                 dir=self.working_dir, 
                                                 delete=False)
        output_file = tempfile.NamedTemporaryFile(prefix='malt_output.conll', 
                                                  dir=self.working_dir, 
                                                  delete=False)
        
        try: 
            # Convert list of sentences to CONLL format.
            for line in taggedsent_to_conll(sentences):
                input_file.write(line)
            input_file.close()
            
            # Generate command to run maltparser.
            cmd =self.generate_malt_command(input_file.name, 
                                            output_file.name,
                                            mode="parse")
            
            # This is a maltparser quirk, it needs to be run 
            # where the model file is. otherwise it goes into an awkward
            # missing .jars or strange -w working_dir problem.
            _current_path = os.getcwd() # Remembers the current path.
            try:
                os.chdir(os.path.split(self.mco)[0]) # Change to modelfile path
            except:
                pass
            ret = self._execute(cmd, verbose) # Run command.
            os.chdir(_current_path) # Change back to current path.
            
            if ret != 0:
                raise Exception("MaltParser parsing (%s) failed with exit "
                                "code %d" % (' '.join(cmd), ret))
            
            # Must return iter(iter(Tree))
            return (iter([dep_graph]) for dep_graph in 
                    DependencyGraph.load(output_file.name))

        finally:
            # Deletes temp files created in the process.
            input_file.close()
            os.remove(input_file.name)
            output_file.close()
            os.remove(output_file.name)
    
    def parse_sents(self, sentences, verbose=False):
        """
        Use MaltParser to parse multiple sentences. 
        Takes a list of sentences, where each sentence is a list of words.
        Each sentence will be automatically tagged with this 
        MaltParser instance's tagger.
        
        :param sentences: Input sentences to parse
        :type sentence: list(list(str))
        :return: iter(DependencyGraph)
        """
        tagged_sentences = [self.tagger.tag(sentence) for sentence in sentences]
        return iter(self.tagged_parse_sents(tagged_sentences, verbose))
    

    def tagged_parse(self, sentence, verbose=False):
        """
        Use MaltParser to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized and
        tagged.
        
        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :return: iter(DependencyGraph) the possible dependency graph 
        representations of the sentence
        """
        return next(self.tagged_parse_sents([sentence], verbose))
        
    def generate_malt_command(self, inputfilename, outputfilename=None, 
                              mode=None):
        """
        This function generates the maltparser command use at the terminal.
        
        :param inputfilename: path to the input file
        :type inputfilename: str
        :param outputfilename: path to the output file
        :type outputfilename: str
        """
        
        cmd = ['java']
        cmd+= self.additional_java_args # Adds additional java arguments.
        cmd+= ['-cp', ':'.join(self.malt_jars)] # Adds classpaths for jars
        cmd+= ['org.maltparser.Malt'] # Adds the main function.
        ##cmd+= ['-w', self.working_dir]
        # Adds the model file.
        if os.path.exists(self.mco): # when parsing
            cmd+= ['-c', os.path.split(self.mco)[-1]] 
        else: # when learning
            cmd+= ['-c', self.mco]
        
        cmd+= ['-i', inputfilename]
        if mode == 'parse':
            cmd+= ['-o', outputfilename]
        cmd+= ['-m', mode] # mode use to generate parses.
        return cmd
        
    @staticmethod
    def _execute(cmd, verbose=False):
        output = None if verbose else subprocess.PIPE
        p = subprocess.Popen(cmd, stdout=output, stderr=output)
        return p.wait()

    def train(self, depgraphs, verbose=False):
        """
        Train MaltParser from a list of ``DependencyGraph`` objects
        
        :param depgraphs: list of ``DependencyGraph`` objects for training input data
        """
        input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
                                                 dir=self.working_dir,
                                                 delete=False)
        try:
            input_str = ('\n'.join(dg.to_conll(10) for dg in depgraphs))
            input_file.write(input_str.encode("utf8"))
            input_file.close()
            self.train_from_file(input_file.name, verbose=verbose)
        finally:
            input_file.close()
            os.remove(input_file.name)
            
    def train_from_file(self, conll_file, verbose=False):
        """
        Train MaltParser from a file
    
        :param conll_file: str for the filename of the training input data
        """

        # If conll_file is a ZipFilePathPointer, then we need to do some extra
        # massaging
        if isinstance(conll_file, ZipFilePathPointer):
            input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
                                                    dir=self.working_dir,
                                                    delete=False)
            try:
                conll_str = conll_file.open().read()
                conll_file.close()
                input_file.write(conll_str)
                input_file.close()
                return self.train_from_file(input_file.name, verbose=verbose)
            finally:
                input_file.close()
                os.remove(input_file.name)

        # Generate command to run maltparser.
        cmd =self.generate_malt_command(conll_file,
                                        mode="learn")
        
        ret = self._execute(cmd, verbose)
        if ret != 0:
            raise Exception("MaltParser training (%s) "
                            "failed with exit code %d" %
                            (' '.join(cmd), ret))

        self._trained = True
        
def demo(path_to_maltparser):
    dg1 = DependencyGraph("""1    John    _    NNP   _    _    2    SUBJ    _    _
                         2    sees    _    VB    _    _    0    ROOT    _    _
                         3    a       _    DT    _    _    4    SPEC    _    _
                         4    dog     _    NN    _    _    2    OBJ     _    _
                      """)
    dg2 = DependencyGraph("""1    John    _    NNP   _    _    2    SUBJ    _    _
                             2    walks   _    VB    _    _    0    ROOT    _    _
                          """)
    
    verbose = False
    maltParser = MaltParser(path_to_maltparser=path_to_maltparser)
    
    maltParser.train([dg1,dg2], verbose=verbose)
    
    maltParser.parse_one(['John','sees','Mary']).tree().pprint()
    maltParser.parse_one(['a','man','runs']).tree().pprint()
    
    next(maltParser.tagged_parse([('John','NNP'),('sees','VB'),('Mary','NNP')], 
                                 verbose)).tree().pprint()


def config_malt(bin=None, verbose=False, path_to_malt_libs=None):
    """
    Configure NLTK's interface to the ``malt`` package.  This
    searches for a directory containing the malt jar

    :param bin: The full path to the ``malt`` binary.  If not
        specified, then nltk will search the system for a ``malt``
        binary; and if one is not found, it will raise a
        ``LookupError`` exception.
    :type bin: str
    """        
    #: A list of directories that should be searched for the malt
    #: executables.  This list is used by ``config_malt`` when searching
    #: for the malt executables.
    _malt_path = ['.',
                 '/usr/lib/malt-1*',
                 '/usr/share/malt-1*',
                 '/usr/local/bin',
                 '/usr/local/malt-1*',
                 '/usr/local/bin/malt-1*',
                 '/usr/local/malt-1*',
                 '/usr/local/share/malt-1*']

    if path_to_malt_libs:
        _malt_path.append(path_to_malt_libs)
    
    # Expand wildcards in _malt_path:
    malt_path = reduce(add, map(glob.glob, _malt_path))

    # Find the malt binary.
    malt_bin = find_binary('malt.jar', bin, searchpath=malt_path, 
                                env_vars=['MALT_PARSER'], 
                                url='http://www.maltparser.org/', 
                                verbose=verbose)
    return malt_bin

if __name__ == '__main__':
    # Test if magic find_binary still works but maybe it should be deprecated.
    malt_binary_file = config_malt()
    demo('/home/username/maltparser-1.8/')
