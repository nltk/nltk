# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os, sys, bisect, re, textwrap
from itertools import islice
from nltk import tokenize
from nltk.etree import ElementTree

from nltk.corpus.reader.plaintext import PlaintextCorpusReader
from nltk.corpus.reader.util import find_corpus_items
from nltk.corpus.reader.brown import TaggedCorpusReader
from nltk.corpus.reader.cmudict import CMUDictCorpusReader
from nltk.corpus.reader.conll import ConllChunkCorpusReader
from nltk.corpus.reader.wordlist import WordListCorpusReader
from nltk.corpus.reader.gutenberg import GutenbergCorpusReader
from nltk.corpus.reader.xmldocs import XMLCorpusReader
from nltk.corpus.reader.ppattach import PPAttachmentCorpusReader
from nltk.corpus.reader.senseval import SensevalCorpusReader
from nltk.corpus.reader.ieer import IEERCorpusReader
from nltk.corpus.reader.treebank import TreebankCorpusReader
from nltk.corpus.reader.sinica_treebank import SinicaTreebankCorpusReader
from nltk.corpus.reader.indian import IndianCorpusReader
from nltk.corpus.reader.toolbox import ToolboxCorpusReader
from nltk.corpus.reader.timit import TimitCorpusReader

######################################################################
#{ Corpus Loader
######################################################################

def load_nltk_corpora(searchpath='', verbose=False):
    """
    Construct a corpus reader for each of the corpora in the NLTK
    corpus package, and return them as a dictionary mapping from
    corpus names to corpus readers.  Corpus directories will be
    searched for in a standard set of locations.  This set of
    locations can be extended in two ways: by using the NLTK_CORPORA
    environment varibale; and by using the C{searchpath} parameter.

    @param verbose: If true, then print warning messages for missing
       corpora.
    """
    # Construct the search path.
    searchpath = (searchpath.split(':')  +
                  os.environ.get('NLTK_CORPORA','').split(':') +
                  _CORPUS_PATH)
    # Filter out any directories that don't exist.
    searchpath = [d for d in searchpath if os.path.exists(d)]

    # Define a function to automate the process of constructing
    # CorpusNotFound placeholder for missing corpora.
    readers = {}
    def add_reader(corpus_name, reader_cls, *args):
        # Search for the corpus, using our search path.
        try: corpus_dir = find_corpus(corpus_name, searchpath)
        except LookupError: corpus_dir = None

        # If we found it, construct a reader for it.
        if corpus_dir is not None:
            readers[corpus_name] = reader_cls(corpus_dir, *args)

        # If we didn't find it, construct a 'CorpusNotFound' placehold.
        else:
            readers[corpus_name] = CorpusNotFound(corpus_name)
            if verbose:
                print 'Warning: corpus %s not found' % corpus_name

    # Add all the standard corpora!
    add_reader('abc', PlaintextCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('brown', TaggedCorpusReader, list('abcdefghjklmnpr'))
    add_reader('cmudict', CMUDictCorpusReader, ['cmudict'])
    add_reader('conll2000', ConllChunkCorpusReader,
               ['train', 'test'], '.txt', ('NP','VP','PP'))
    add_reader('conll2002', ConllChunkCorpusReader,
               ['ned.train', 'ned.testa', 'ned.testb',
                'esp.train', 'esp.testa', 'ned.testb'], '',
               ('LOC', 'PER', 'ORG', 'MISC'))
    add_reader('genesis', PlaintextCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('gutenberg', GutenbergCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('ieer', IEERCorpusReader, '(?!README|\.svn).*')
    add_reader('inaugural', PlaintextCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('indian', IndianCorpusReader, '(?!\.svn).*', '.pos')
    add_reader('names', WordListCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('ppattach', PPAttachmentCorpusReader,
               ['training', 'test', 'devset'])
    add_reader('senseval', SensevalCorpusReader, '(?!\.svn).*', '.pos')
    add_reader('shakespeare', XMLCorpusReader, '(?!\.svn).*', '.xml')
    add_reader('sinica_treebank', SinicaTreebankCorpusReader, ['parsed'])
    add_reader('state_union', PlaintextCorpusReader, '(?!\.svn).*', '.txt')
    add_reader('stopwords', WordListCorpusReader, '(?!README|\.svn).*')
    add_reader('timit', TimitCorpusReader)
    add_reader('toolbox', ToolboxCorpusReader,
               '(?!.*(README|\.svn)).*\.(dic|txt)')
    add_reader('treebank', TreebankCorpusReader)
    add_reader('udhr', PlaintextCorpusReader, '(?!README|\.svn).*')
    add_reader('webtext', PlaintextCorpusReader, '(?!README|\.svn).*')
    add_reader('words', WordListCorpusReader, '(?!README|\.svn).*')

    return readers

"""
chat80, ycoe
"""

######################################################################
#{ Finding Corpus Directories & Files
######################################################################

def find_corpus(corpus_dir, searchpath=None):
    """
    Search for the given corpus directory in the given search path.
    If the corpus directory name conains multiple path components,
    then they should be expressed using '/', which will automatically
    be converted to the appropriate path component separator.
    """
    if searchpath is None:
        searchpath = _CORPUS_PATH
    corpus_dir = os.path.join(*corpus_dir.split('/'))
    for directory in searchpath:
        p = os.path.join(directory, corpus_dir)
        if os.path.exists(p):
            return p
        
    raise LookupError('Corpus not found!')

def find_corpus_file(corpusname, filename, extension=None):
    # Look for it in the corpus
    if not os.path.isabs(filename):
        corpusname = os.path.join(*corpusname.split('/'))
        p = os.path.join(find_corpus(corpusname), filename)
        if extension: p += extension
        if os.path.exists(p):
            return p
    raise LookupError('File %r in corpus %r not found' %
                      (filename, corpusname))

######################################################################
#{ Missing Corpora
######################################################################

class CorpusNotFound:
    def __init__(self, corpus_name):
        self._corpus_name = corpus_name

    URL = '<http://nltk.org/index.php/Installation>'
        
    def __getattr__(self, attr):
        msg = textwrap.fill(
            'Corpus %r not found.  For installation instructions, '
            'please see %s.' % (self._corpus_name, self.URL),
            initial_indent='  ',subsequent_indent='  ', width=66)
        sep = '*'*70
        corpus_not_found = '\n%s\n%s\n%s' % (sep, msg, sep)
        raise ValueError(corpus_not_found)

######################################################################
#{ Corpus Path
######################################################################

#: A list of directories that should be searched for corpora. This
#: list should probably be expanded and/or cleaned up at some point.
_CORPUS_PATH = [
    # Common locations on Windows:
    r'C:\corpora', r'D:\corpora', r'E:\corpora',
    os.path.join(sys.prefix, 'nltk', 'corpora'),
    os.path.join(sys.prefix, 'lib', 'nltk', 'corpora'),
    os.path.join(sys.prefix, 'nltk'),
    os.path.join(sys.prefix, 'lib', 'nltk'),
    # Common locations on UNIX & OS X:
    '/usr/share/nltk/corpora',
    '/usr/local/share/nltk/corpora',
    '/usr/share/nltk',
    '/usr/local/share/nltk',
    '/usr/share/nltk_lite/corpora',
    '/usr/local/share/nltk_lite/corpora',
    os.path.expanduser('~/nltk/corpora'),
    os.path.expanduser('~/corpora/nltk'),
    ]

