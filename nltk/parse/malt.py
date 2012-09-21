# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2012 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile
import glob
from operator import add
import subprocess

from nltk.data import ZipFilePathPointer
from nltk.tag import RegexpTagger
from nltk.tokenize import word_tokenize
from nltk.internals import find_binary

from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph

class MaltParser(ParserI):

    def __init__(self, tagger=None, mco=None, working_dir=None):
        """
        An interface for parsing with the Malt Parser.

        :param mco: The name of the pre-trained model. If provided, training
            will not be required, and MaltParser will use the model file in
            ${working_dir}/${mco}.mco.
        :type mco: str
        """
        self.config_malt()
        self.mco = 'malt_temp' if mco is None else mco
        self.working_dir = tempfile.gettempdir() if working_dir is None\
                           else working_dir
        self._trained = mco is not None

        if tagger is not None:
            self.tagger = tagger
        else:
            self.tagger = RegexpTagger(
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

        # Expand wildcards in _malt_path:
        malt_path = reduce(add, map(glob.glob, _malt_path))

        # Find the malt binary.
        self._malt_bin = find_binary('malt.jar', bin,
            searchpath=malt_path, env_vars=['MALTPARSERHOME'],
            url='http://www.maltparser.org/',
            verbose=verbose)

    def parse(self, sentence, verbose=False):
        """
        Use MaltParser to parse a sentence. Takes a sentence as a list of
        words; it will be automatically tagged with this MaltParser instance's
        tagger.

        :param sentence: Input sentence to parse
        :type sentence: list(str)
        :return: ``DependencyGraph`` the dependency graph representation of the sentence
        """
        taggedwords = self.tagger.tag(sentence)
        return self.tagged_parse(taggedwords, verbose)

    def raw_parse(self, sentence, verbose=False):
        """
        Use MaltParser to parse a sentence. Takes a sentence as a string;
        before parsing, it will be automatically tokenized and tagged with this
        MaltParser instance's tagger.

        :param sentence: Input sentence to parse
        :type sentence: str
        :return: ``DependencyGraph`` the dependency graph representation of the sentence
        """
        words = word_tokenize(sentence)
        return self.parse(words, verbose)

    def tagged_parse(self, sentence, verbose=False):
        """
        Use MaltParser to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized and
        tagged.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :return: ``DependencyGraph`` the dependency graph representation of the sentence
        """

        if not self._malt_bin:
            raise Exception("MaltParser location is not configured.  Call config_malt() first.")
        if not self._trained:
            raise Exception("Parser has not been trained.  Call train() first.")

        input_file = tempfile.NamedTemporaryFile(prefix='malt_input.conll',
                                                 dir=self.working_dir,
                                                 delete=False)
        output_file = tempfile.NamedTemporaryFile(prefix='malt_output.conll',
                                                 dir=self.working_dir,
                                                 delete=False)

        try:
            for (i, (word, tag)) in enumerate(sentence, start=1):
                input_file.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' %
                        (i, word, '_', tag, tag, '_', '0', 'a', '_', '_'))
            input_file.write('\n')
            input_file.close()

            cmd = ['java', '-jar', self._malt_bin, '-w', self.working_dir,
                   '-c', self.mco, '-i', input_file.name,
                   '-o', output_file.name, '-m', 'parse']

            ret = self._execute(cmd, verbose)
            if ret != 0:
                raise Exception("MaltParser parsing (%s) failed with exit "
                                "code %d" % (' '.join(cmd), ret))

            return DependencyGraph.load(output_file.name)
        finally:
            input_file.close()
            os.remove(input_file.name)
            output_file.close()
            os.remove(output_file.name)

    def train(self, depgraphs, verbose=False):
        """
        Train MaltParser from a list of ``DependencyGraph`` objects

        :param depgraphs: list of ``DependencyGraph`` objects for training input data
        """
        input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
                                                 dir=self.working_dir,
                                                 delete=False)
        try:
            input_file.write('\n'.join([dg.to_conll(10) for dg in depgraphs]))
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
        if not self._malt_bin:
            raise Exception("MaltParser location is not configured.  Call config_malt() first.")

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

        cmd = ['java', '-jar', self._malt_bin, '-w', self.working_dir,
               '-c', self.mco, '-i', conll_file, '-m', 'learn']

        ret = self._execute(cmd, verbose)
        if ret != 0:
            raise Exception("MaltParser training (%s) "
                            "failed with exit code %d" %
                            (' '.join(cmd), ret))

        self._trained = True

    @staticmethod
    def _execute(cmd, verbose=False):
        output = None if verbose else subprocess.PIPE
        p = subprocess.Popen(cmd, stdout=output, stderr=output)
        return p.wait()


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

    print maltParser.raw_parse('John sees Mary', verbose=verbose).tree().pprint()
    print maltParser.raw_parse('a man runs', verbose=verbose).tree().pprint()

if __name__ == '__main__':
    demo()
